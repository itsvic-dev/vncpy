{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      flake-utils,
      nixpkgs,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        packages.default =
          with pkgs.python3Packages;
          buildPythonApplication {
            pname = "vncpy";
            version = "1.0.0";
            pyproject = true;
            src = ./.;

            build-system = [
              setuptools
              wheel
            ];

            dependencies = [ pillow ];
          };
      }
    );
}
