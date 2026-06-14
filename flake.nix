{
  description = "LAN Game of battleships, made with pygame.";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$REPO_ROOT";
      };

      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python3;
        in
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
            ]
          )
      );

    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet = pythonSets.${system}.overrideScope editableOverlay;
          virtualenv = pythonSet.mkVirtualEnv "battleships-pygame-dev-env" workspace.deps.all;
          runtimeLibs = with pkgs; [
            libGL
            libxkbcommon
            wayland
            wayland-protocols
            libdecor

            libX11
            libXcursor
            libXext
            libXinerama
            libXi
            libXrandr
          ];
        in
        {
          default = pkgs.mkShell {
            packages = [
              virtualenv
              pkgs.uv
            ]
            ++ runtimeLibs;
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = pythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";

              SDL_VIDEODRIVER = "wayland,x11";

              LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath runtimeLibs;
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              export LD_LIBRARY_PATH=${pkgs.libpulseaudio}/lib:$LD_LIBRARY_PATH
            '';
          };
        }
      );

      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          venv = pythonSets.${system}.mkVirtualEnv "battleships-pygame-env" workspace.deps.default;

          runtimeLibs = with pkgs; [
            libGL
            libxkbcommon
            wayland
            wayland-protocols
            libdecor
            libX11
            libXcursor
            libXext
            libXinerama
            libXi
            libXrandr
            libpulseaudio
          ];

          wrappedApp =
            pkgs.runCommand "battleship-pygame-lan-wrapped"
              {
                nativeBuildInputs = [ pkgs.makeWrapper ];
              }
              ''
                mkdir -p $out/bin $out/share/battleship-pygame-lan
                cp -R ${./src/battleship_pygame_lan/gui/assets} $out/share/battleship-pygame-lan/assets
                makeWrapper ${venv}/bin/battleship-pygame-lan $out/bin/battleship-pygame-lan \
                  --prefix LD_LIBRARY_PATH : "${pkgs.lib.makeLibraryPath runtimeLibs}" \
                  --set SDL_VIDEODRIVER "wayland,x11" \
                  --set BATTLESHIP_ASSETS_DIR "$out/share/battleship-pygame-lan/assets"
              '';

          desktopItem = pkgs.makeDesktopItem {
            name = "battleship-pygame-lan";
            desktopName = "Battleships (LAN)";
            exec = "battleship-pygame-lan";
            comment = "LAN Game of battleships, made with pygame.";
            categories = [
              "Game"
              "BoardGame"
            ];
          };
        in
        {
          default = pkgs.symlinkJoin {
            name = "battleship-pygame-lan";
            paths = [
              wrappedApp
              desktopItem
            ];
          };
        }
      );

      nixosModules.default = import ./nix/module.nix self;
    };
}
