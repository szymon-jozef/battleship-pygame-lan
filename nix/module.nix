self:
{
  config,
  lib,
  pkgs,
}:
let
  inherit (pkgs.stdenv.hostPlatform) system;
  cfg = config.programs.battleship-pygame-lan;
  port = 6769;
in
{
  options = {
    programs.battleship-pygame-lan = {
      enable = lib.mkEnableOption "Battleship Pygame LAN game";

      package = lib.mkOption {
        type = lib.types.package;
        default = self.packages.${system}.default;
        description = "Program package to use";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    networking.firewall.allowedTCPPorts = [ port ];
    environment.systemPackages = [ cfg.package ];
  };
}
