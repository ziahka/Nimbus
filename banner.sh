#!/bin/bash

echo -ne "\\033[2J\033[3;1f"
eval "cat ~/Nimbus/assets/banner.txt"
printf "\n\n\033[1;32mNimbus is running!\033[0m"
