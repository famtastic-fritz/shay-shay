# nix/packages.nix — Shay-Shay package built with uv2nix
{ inputs, ... }:
{
  perSystem =
    { pkgs, inputs', ... }:
    let
      shayAgent = pkgs.callPackage ./shay-shay.nix {
        inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
        npm-lockfile-fix = inputs'.npm-lockfile-fix.packages.default;
        # Only embed clean revs — dirtyRev doesn't represent any upstream
        # commit, so comparing it would always claim "update available".
        rev = inputs.self.rev or null;
      };
    in
    {
      packages = {
        default = shayAgent;
        tui = shayAgent.shayTui;
        web = shayAgent.shayWeb;

        fix-lockfiles = shayAgent.shayNpmLib.mkFixLockfiles {
          packages = [ shayAgent.shayTui shayAgent.shayWeb ];
        };
      };
    };
}
