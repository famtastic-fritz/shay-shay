# nix/web.nix — Shay-Shay Web Dashboard (Vite/React) frontend build
{ pkgs, shayNpmLib, ... }:
let
  src = ../web;
  npmDeps = pkgs.fetchNpmDeps {
    inherit src;
    hash = "sha256-HWB1piIPglTXbzQHXFYHLgVZIbDb60esupXSQGa1+lI=";
  };

  npm = shayNpmLib.mkNpmPassthru { folder = "web"; attr = "web"; pname = "shay-web"; };

  packageJson = builtins.fromJSON (builtins.readFile (src + "/package.json"));
  version = packageJson.version;
in
pkgs.buildNpmPackage (npm // {
  pname = "shay-web";
  inherit src npmDeps version;

  doCheck = false;

  buildPhase = ''
    npx tsc -b
    npx vite build --outDir dist
  '';

  installPhase = ''
    runHook preInstall
    cp -r dist $out
    runHook postInstall
  '';
})
