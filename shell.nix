with import <nixpkgs> {};

mkShell {
  packages = [
    uv
    python313
    stdenv.cc.cc
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
  '';
}