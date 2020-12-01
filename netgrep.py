#!/usr/bin/env python3

"""Print lines that match a provided list of networks or member addresses
within the networks.
"""
__author__ = "Phillip Stansell"
__version__ = "0.92"

import argparse
import ipaddress
import sys
try:
    import colorama
except ImportError:
    COLORAMA_IMPORTED = False
else:
    COLORAMA_IMPORTED = True
    from colorama import Fore, Style


def _build_output_line(parts: dict, colorize: bool) -> str:
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

def _clean_up_networks(strings: list) -> tuple:
    """
    Take a list of strings. Convert elements to objects from the ipaddress
    class. For elements that fail conversion (still string), print an error and
    remove them. Separate remaining items into lists of a single address family:
    one of IPv4 objects and the other of IPv6 objects. Return a tuple of the
    IPv4Network list, IPv6Network list.
    """

    # Get two empty lists ready
    ip4_nets = []
    ip6_nets = []

    # Convert strings to ipaddress objects
    ip_networks = _strings_to_networks(strings)

    # Print an error for each string that did not convert and remove it from
    # the list. Sort IPv4 and IPv6 objects into separate lists.
    for i,item in enumerate(ip_networks):
        if isinstance(item, str):
            print("ValueError: '{}' does not appear to be an IPv4 or IPv6 "
                    "network, ignoring.".format(item))
            del ip_networks[i]
        elif isinstance(item, ipaddress.IPv4Network):
            ip4_nets.append(item)
        elif isinstance(item, ipaddress.IPv6Network):
            ip6_nets.append(item)
        else:
            raise TypeError("Unexpected type for item {} found at "
            "'ip_networks[{}]'.".format(str(item), i))

    # Return collapsed lists
    return (list(ipaddress.collapse_addresses(ip4_nets)),
            list(ipaddress.collapse_addresses(ip6_nets)))

def _read_networks_files(file_list: list) -> list:
    """
    Take a list of file names. Read each line from all files into a list.
    Return the list.
    """
    network_strings = []

    # Read network list from files
    for net_file in file_list:
        try:
            net_f = open(net_file, "r")
        except OSError:
            print("Could not open file '{}', skipping.".format(net_file), file=sys.stderr)
        else:
            while True:
                # Read the next line of the file
                line = net_f.readline()

                # Empty line indicates EOF
                if not line:
                    break

                # Add non-empty lines to the list with the new line stripped
                network_strings.append(line.strip("\n"))

    return network_strings

def _search_files(files: list, ipv4_networks: list, ipv6_networks: list, colorize: bool):
    """
    Take a list of file names. For each file search for matches to the network
    list. Print any lines with at least one match.
    """
    for target in files:
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
                matches = _search_tokens(line_tokens, ipv4_networks, ipv6_networks)
                # If we found a match, print the line
                if len(matches) > 0:
                    print(_build_output_line({"file_name": target,
                        "line_number": count,
                        "line_tokens": line_tokens,
                        "matched_tokens": matches}, colorize))
        finally:
            # Close opened file
            target_file.close()

def _search_tokens(tokens: list, ipv4_networks: list, ipv6_networks: list) -> list:
    """
    Take a list of strings, a list of IPv4Network objects, and a list of
    IPv6Network objects. Return a list of indexes from the first list that were
    found within a network from the second or third list.
    """
    result = []
    # Convert tokens to IPv4Network or IPv6Network objects
    ip_tokens = _strings_to_networks(tokens)

    # If any token has converted to an ipaddress object, check if it is a
    # subnet of any member of the matching address family list. For sucessful
    # subnet matches, add the ip_token list index to the result list.
    for i, token in enumerate(ip_tokens):
        if isinstance(token, ipaddress.IPv4Network):
            # For host length networks, look ahead to the next token. If that
            # is a subnet mask or host mask, replace both tokens with the
            # corrected network.
            if token.prefixlen == 32 and (i + 1) < len(ip_tokens):
                j = i + 1
                next_token = ip_tokens[j]
                if isinstance(next_token, ipaddress.IPv4Network) and next_token.prefixlen == 32:
                    new_token = _strings_to_networks([ str(token.network_address)
                        + "/"
                        + str(next_token.network_address) ])[0]
                    if isinstance(new_token, ipaddress.IPv4Network):
                        token = new_token
                        ip_tokens[j] = new_token

            # Check if IPv4Network object is subnet of any ipv4_networks list
            # member. Break the loop on first match.
            for net in ipv4_networks:
                if token.subnet_of(net):
                    # print("Token {} matched network {}.".format(token, net))
                    result.append(i)
                    break
        elif isinstance(token, ipaddress.IPv6Network):
            # Check if IPv6Network object is subnet of any ipv6_networks list
            # member. Break the loop on first match.
            for net in ipv6_networks:
                if token.subnet_of(net):
                    result.append(i)
                    break

    return result

def _strings_to_networks(strings: list) -> list:
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
                result.append(ipaddress.ip_interface(item).network)
            except ValueError:
                result.append(item)

    return result

def main():
    """
    search files for instances of a network or its subnets
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Search files for instances of a "
            "network or its subnets")
    parser.add_argument("--color",
            choices=["never", "always", "auto"],
            default="never",
            help="colorize the output when: never (default), always, or auto")
    parser.add_argument("-V", "--version",
            action="version",
            version="%(prog)s " + __version__)
    parser.add_argument("-f", "--file",
            action="append",
            dest="networks_file",
            help="obtain networks from NETWORKS_FILE, one per line; may be "
            "specified multiple times; alternative to specifying a network "
            "before the target_files list",
            required=False)
    parser.add_argument("network",
            action="store",
            help="a single network to find; cannot be used with -f (--file)",
            nargs="*")
    parser.add_argument("target_files",
            help="target files to be checked for matches in the network list",
            nargs="+")
    args = parser.parse_args()

    # Handle color option
    if args.color != "never" and not COLORAMA_IMPORTED:
        print("NOTICE: For color support, install the 'colorama' python module.", file=sys.stderr)
    elif args.color == "auto" and COLORAMA_IMPORTED:
        colorize = True
        colorama.init()
    elif args.color == "always" and COLORAMA_IMPORTED:
        colorize = True
        colorama.init(strip=False)
    else:
        colorize = False

    # Handle network and file arguments
    if args.networks_file is not None:
        # Consider the first positional argument to be a target file instead of a network
        target_files = args.network + args.target_files
        # Populate networks from files
        network_strings = _read_networks_files(args.networks_file)
    else:
        network_strings = args.network
        target_files = args.target_files

    # Convert network strings to ipaddress objects
    ipv4_networks, ipv6_networks = _clean_up_networks(network_strings)

    # print("network_strings: {}".format(network_strings))
    # print("target_files: {}".format(target_files))
    # print("ipv4_networks: {}".format(ipv4_networks))
    # print("ipv6_networks: {}".format(ipv6_networks))

    # Process each target file
    _search_files(target_files, ipv4_networks, ipv6_networks, colorize)

if __name__ == "__main__":
    main()
