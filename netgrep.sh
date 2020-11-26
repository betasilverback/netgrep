#!/usr/bin/env bash

#######################
##  MAIN
#######################
# set a default files path
files="$HOME/repos/*/configs/*"
# set region list
regions=(ams2 dal2 nyj004 sin3 sjc2)
OPTIND=1;

while getopts ":hf:" opt;
do
  case ${opt} in
    h )
      echo "Usage:"
      echo "    netgrep [-h] -f /path/to/files NETWORKS"
      echo ""
      echo "    -h                    Display this help message."
      echo "    -f /path/to/file(s)   A list of files to search."
      exit 0
      ;;
    f )
      files=$OPTARG
      ;;
    \? )
      echo "Invalid option: $OPTARG"
      exit 1
      ;;
    : )
      echo "Invalid option: $OPTARG requires and argument"
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

addr_list="$(cidr-to-ip.sh $@ | sort -V | uniq)"
# echo ""
# echo "Looking for $@ and member addresses."
for addr in ${addr_list[@]}; 
do
  grep -Hn "$addr" "$files";
done

exit 0
