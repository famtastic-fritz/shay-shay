# nix/tui.nix — Shay-Shay TUI (Ink/React) compiled with tsc and bundled
{ pkgs, shayNpmLib, ... }:
let
  src = ../ui-tui;
  npmDeps = pkgs.fetchNpmDeps {
    inherit src;
    hash = "sha256-9r1EYQ600gNXOnNXwakorpEk7hS/FPxZVbB2JksrhYs=";
  };

  npm = shayNpmLib.mkNpmPassthru { folder = "ui-tui"; attr = "tui"; pname = "shay-tui"; };

  packageJson = builtins.fromJSON (builtins.readFile (src + "/package.json"));
  version = packageJson.version;
in
pkgs.buildNpmPackage (npm // {
  pname = "shay-tui";
  inherit src npmDeps version;

  doCheck = false;
  npmFlags = [ "--legacy-peer-deps" ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/shay-tui

    # Single self-contained bundle built by scripts/build.mjs (esbuild).
    cp -r dist $out/lib/shay-tui/dist

    # package.json kept for "type": "module" resolution on `node dist/entry.js`.
    cp package.json $out/lib/shay-tui/

    runHook postInstall
  '';
})
