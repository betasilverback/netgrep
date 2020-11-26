#!/usr/bin/env python3

"""Print lines that match a provided list of networks or member addresses
within the networks.
"""
__author__ = "Phillip Stansell"
__version__ = "0.9"

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

def search_networks(tokens: list, networks: list) -> list:
    """
    Take a list of strings and a list of IPv[46]Network objects and return a
    list of indexes from the first list that were found within a network from
    the second list.
    """
    result = []
    # Convert tokens to IPv[46]Network or IPv[46]Interface objects
    ip_tokens = strings_to_networks(tokens)

    # If any networks are found in the line, print it
    for i, token in enumerate(ip_tokens):
        if isinstance(token, (ipaddress.IPv4Interface, ipaddress.IPv6Interface)):
            token = token.network
        if isinstance(token, ipaddress.IPv4Network):
            for net in [ net4 for net4 in networks if isinstance(net4, ipaddress.IPv4Network) ]:
                if token.subnet_of(net):
                    result.append(i)
                    break
        elif isinstance(token, ipaddress.IPv6Network):
            for net in [ net6 for net6 in networks if isinstance(net6, ipaddress.IPv6Network) ]:
                if token.subnet_of(net):
                    result.append(i)
                    break

    return result

def strings_to_networks(strings: list) -> list:
    """
    Take a list of strings and return a list with elements converted to objects
    of type IPv4Network or IPv6Network where possible. Strings that could not be
    converted are copied.
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
    ip_networks = strings_to_networks(args.networks)
    # Print an error for each network string that did not convert and remove
    # it from the list. Convert any IPv[46]Interface objects to IPv[46]Network
    # objects.
    for i,item in enumerate(ip_networks):
        if isinstance(item, str):
            print("ValueError: '{}' does not appear to be an IPv4 or IPv6 "
                    "network, ignoring.".format(item))
            del ip_networks[i]
        if isinstance(item, (ipaddress.IPv4Interface, ipaddress.IPv6Interface)):
            ip_networks[i] = item.network

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
                matches = search_networks(line_tokens, ip_networks)
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
