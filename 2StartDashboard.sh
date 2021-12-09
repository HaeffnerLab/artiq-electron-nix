#!/bin/bash

# Start artiq_dashboard
cd electron/artiq-master 
nix-shell my-artiq-env.nix
artiq_dashboard
