#!/usr/bin/env python3

"""Print lines that match a provided list of networks or member addresses
within the networks.
"""
__author__ = "Phillip Stansell"
__version__ = "0.91"

import argparse
import ipaddress
try:
    import colorama
except ImportError:
    COLORAMA_IMPORTED = False
else:
    COLORAMA_IMPORTED = True
    from colorama import Fore, Style
    colorama.init(autoreset=True)

color = {
    "PURPLE": "\033[95m",
    "CYAN": "\033[96m",
    "DARKCYAN": "\033[36m",
    "BLUE": "\033[94m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
    "END": "\033[0m" }

def build_output_line(parts: dict, colorize: bool) -> str:
    """
    Take a dictionary with the following keys:
        'file_name': str
        'line_number': int
        'line_tokens': list of str
        'matched_tokens': list of int

    A string that combines these components is returned. If 'colorize' is True,
    some elements are nicely colorized in the string.
    """
    sep = ":"
    if colorize and COLORAMA_IMPORTED:
        sep = Fore.CYAN + sep + Style.RESET_ALL
        parts["file_name"] = Fore.MAGENTA + parts["file_name"] + Style.RESET_ALL
        parts["line_number"] = Fore.GREEN + str(parts["line_number"]) + Style.RESET_ALL
        for match in parts["matched_tokens"]:
            parts["line_tokens"][match] = ( Style.BRIGHT +
                    Fore.RED +
                    parts["line_tokens"][match] +
                    Style.RESET_ALL )

    result = "{fn}{sp}{ln}{sp}{li}".format(fn=parts["file_name"],
            ln=parts["line_number"],
            li=" ".join(parts["line_tokens"]),
            sp=sep)

    return result

def clean_up_networks(strings: list) -> tuple:
    """
    Take a list of strings. Convert elements to objects from the ipaddress
    class. For elements that fail conversion (still string), print an error and
    remove them. Separate remaining items into lists of a single address family:
    one of IPv4 objects and the other of IPv6 objects. Convert Interface objects
    to Network objects before inserting into the appropriate address family
    list. Return a tuple of the IPv4Network list, IPv6Network list.
    """
    ip4_nets = []
    ip6_nets = []
    # Convert strings to ipaddress objects
    ip_networks = strings_to_networks(strings)

    # Print an error for each string that did not convert and remove it from
    # the list. Sort IPv4 and IPv6 objects into separate lists while converting
    # any Interface objects to Network objects.
    for i,item in enumerate(ip_networks):
        if isinstance(item, str):
            print("ValueError: '{}' does not appear to be an IPv4 or IPv6 "
                    "network, ignoring.".format(item))
            del ip_networks[i]
        elif isinstance(item, ipaddress.IPv4Interface):
            ip4_nets.append(item.network)
        elif isinstance(item, ipaddress.IPv4Network):
            ip4_nets.append(item)
        elif isinstance(item, ipaddress.IPv6Interface):
            ip6_nets.append(item.network)
        elif isinstance(item, ipaddress.IPv6Network):
            ip6_nets.append(item)
        else:
            raise TypeError("Unexpected type for item {} found at "
            "'ip_networks[{}]'.".format(str(item), i))

    # Return collapsed lists
    return (list(ipaddress.collapse_addresses(ip4_nets)),
            list(ipaddress.collapse_addresses(ip6_nets)))

def search_networks(tokens: list, ipv4_networks: list, ipv6_networks: list) -> list:
    """
    Take a list of strings, a list of IPv4Network objects, and a list of
    IPv6Network objects. Return a list of indexes from the first list that were
    found within a network from the second or third list.
    """
    result = []
    # Convert tokens to IPv[46]Network or IPv[46]Interface objects
    ip_tokens = strings_to_networks(tokens)

    # If any token has converted to an ipaddress object, check if it is a
    # subnet of any member of the matching address family list. For sucessful
    # subnet matches, add the ip_token list index to the result list.
    for i, token in enumerate(ip_tokens):
        # Convert any Interface objects to Network Objects
        if isinstance(token, (ipaddress.IPv4Interface, ipaddress.IPv6Interface)):
            token = token.network

        if isinstance(token, ipaddress.IPv4Network):
            # For host length networks, look ahead to the next token. If is a
            # subnet mask or host mask, replace both tokens with the corrected
            # network.
            if token.prefixlen == 32 and (i + 1) < len(ip_tokens):
                j = i + 1
                next_token = ip_tokens[j]
                if isinstance(next_token, ipaddress.IPv4Network) and next_token.prefixlen == 32:
                    new_token = strings_to_networks([ str(token.network_address)
                        + "/"
                        + str(next_token.network_address) ])[0]
                    if isinstance(new_token, ipaddress.IPv4Interface):
                        new_token = new_token.network
                    if isinstance(new_token, ipaddress.IPv4Network):
                        token = new_token
                        ip_tokens[j] = new_token

            # Check if IPv4Network object is subnet of any ipv4_networks list
            # member.
            for net in ipv4_networks:
                if token.subnet_of(net):
                    # print("Token {} matched network {}.".format(token, net))
                    result.append(i)
                    break
        elif isinstance(token, ipaddress.IPv6Network):
            # Check if IPv6Network object is subnet of any ipv6_networks list
            # member.
            for net in ipv6_networks:
                if token.subnet_of(net):
                    result.append(i)
                    break

    return result

def strings_to_networks(strings: list) -> list:
    """
    Take a list of strings and return a list with elements converted to objects
    of type IPv4Network or IPv6Network where possible. Strings that could not be
    converted are copied unchanged.
    """
    result = []

    for item in strings:
        try:
            result.append(ipaddress.ip_network(item))
        except ValueError:
            try:
                result.append(ipaddress.ip_interface(item))
            except ValueError:
                result.append(item)

    return result

def main():
    """
    search files for instances of a network or its subnets
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="search files for instances of a "
            "network or its subnets")
    parser.add_argument("-c", "--colorize",
            action="store_true",
            default=False,
            help="Colorize the output")
    parser.add_argument("-n", "--network",
            action="append",
            dest="networks",
            help="a network to find; may be specified multiple times",
            required=True)
    parser.add_argument("target_files",
            action="append",
            help="the target files to be checked for matches",
            nargs="*")
    parser.add_argument("-V", "--version",
            action="version",
            version="%(prog)s " + __version__)
    args = parser.parse_args()

    if args.colorize and not COLORAMA_IMPORTED:
        print("NOTICE: For color support, install the 'colorama' python module.")

    # Convert network strings to ipaddress objects
    ipv4_networks, ipv6_networks = clean_up_networks(args.networks)
    # print("ipv4_networks after conversion and collapsing: {}".format(ipv4_networks))
    # print("ipv6_networks after conversion and collapsing: {}".format(ipv6_networks))

    # Flatten list of target files
    targets = [ y for x in args.target_files for y in x ]

    # Process each target file
    for target in targets:
        try:
            target_file = open(target, "r")
        except OSError:
            print("Could not open file '{}', skipping.".format(target))
        else:
            count = 0

            # Process lines in the file
            while True:
                count +=1

                # Get next line from file
                line = target_file.readline()

                # If line is empty end of file is reached
                if not line:
                    break

                # Tokenize the line
                line_tokens = line.strip("\n").split(" ")
                # Get indexes from line_tokens that are within an element of
                # ip_networks
                matches = search_networks(line_tokens, ipv4_networks, ipv6_networks)
                # If we found a match, print the line
                if len(matches) > 0:
                    print(build_output_line({"file_name": target,
                        "line_number": count,
                        "line_tokens": line_tokens,
                        "matched_tokens": matches}, args.colorize))

        finally:
            # Close opened file
            target_file.close()

if __name__ == "__main__":
    main()
