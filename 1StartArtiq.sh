#!/bin/bash

# Start artiq_master
cd electron/artiq-master 
nix-shell my-artiq-env.nix
artiq_master
