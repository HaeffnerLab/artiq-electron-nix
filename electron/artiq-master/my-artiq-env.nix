let
  # pkgs contains the NixOS package collection. ARTIQ depends on some of them, and
  # you may want some additional packages from there.
  pkgs = import <nixpkgs> {};
  artiq-full = import <artiq-full> { inherit pkgs; };
in
  pkgs.mkShell {
    buildInputs = [
      (pkgs.python3.withPackages(ps: [
        # List desired Python packages here.

        # You probably want these two.
        artiq-full.artiq
        artiq-full.artiq-comtools

        # You need a board support package if and only if you intend to flash
        # a board (those packages contain only board firmware).
        # The lines below are only examples, you need to select appropriate
        # packages for your boards.
        # artiq-full.artiq-board-kasli-berkeley4
        #artiq-full.artiq-board-kasli-wipm
        #ps.paramiko  # needed if and only if flashing boards remotely (artiq_flash -H)

        # The NixOS package collection contains many other packages that you may find
        # interesting for your research. Here are some examples:
        #ps.pandas
        ps.numpy
	#ps.PyQt5
        #ps.scipy
        #ps.numba
        (ps.matplotlib.override { enableQt = true; })
        #ps.bokeh
        #ps.cirq
        #ps.qiskit
      ]))

      # List desired non-Python packages here
      #artiq-full.openocd  # needed if and only if flashing boards
      # Other potentially interesting packages from the NixOS package collection:
      #pkgs.gtkwave
      #pkgs.spyder
      #pkgs.R
      #pkgs.julia
      pkgs.qt5.full
      pkgs.qtcreator
    ];
    
    #QT_PLUGIN_PATH="{qt5.qtbase.bin}/lib/qt-${qt5.qtbase.version}/plugins";
  }
