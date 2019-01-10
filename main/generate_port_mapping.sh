#!/bin/bash

for i in {011..254};do
echo "host $(expr $i + 31000) {"
echo "  host-identifier option dhcp-client-identifier \"$(expr $i + 31000)\";"
echo "  fixed-address 10.25.0.$i;"
echo "}"
done

for i in {011..254};do
echo "host $(expr $i + 32000) {"
echo "  host-identifier option dhcp-client-identifier \"$(expr $i + 32000)\";"
echo "  fixed-address 10.25.1.$i;"
echo "}"
done

