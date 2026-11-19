"""Command-line interface for communicating with the HP Prime G2 over USB HID."""

from __future__ import annotations

from pathlib import Path
import sys

import click

from hpprime.files import TYPE_PROGRAM, decode_ppl_source
from hpprime.protocol import HPPrimeG2


def _read_source_file(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def _normalize_source(text: str) -> str:
    return text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


@click.group()
def main() -> None:
    """Send and inspect HP Prime G2 programs over USB HID without Connectivity Kit."""


@main.command()
def info() -> None:
    """Show connected HP Prime G2 hardware and firmware metadata."""
    try:
        with HPPrimeG2() as calc:
            dev = calc.get_info()
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("Model:            HP Prime G2 (VID=0x03F0, PID=0x2441)")
    click.echo(f"Firmware:         {dev.firmware_version}")
    click.echo(f"Build:            {dev.build_number}")
    click.echo(f"Serial:           {dev.serial_number}")
    click.echo(f"Device ID:        {dev.device_id}")
    click.echo(f"Protocol Version: {dev.protocol_version}")


@main.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show all object types, not only PPL programs.")
def list_cmd(show_all: bool) -> None:
    """List PPL programs (or all objects) currently on the calculator."""
    try:
        with HPPrimeG2() as calc:
            calc.connect()
            objects = calc.list_objects()
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if not show_all:
        objects = [obj for obj in objects if obj.file_type == TYPE_PROGRAM]

    if not objects:
        click.echo("No matching objects found.")
        return

    name_w = max(4, max(len(obj.name) for obj in objects))
    type_w = max(4, max(len(obj.type_name) for obj in objects))
    click.echo(f"{'Name':<{name_w}}  {'Type':<{type_w}}  {'Bytes':>7}  {'CRC':<4}  Mode")
    click.echo(f"{'-' * name_w}  {'-' * type_w}  {'-' * 7}  {'-' * 4}  ----")
    for obj in objects:
        crc_str = "OK" if obj.crc_ok else "FAIL"
        mode_str = "zlib" if obj.compressed else "raw"
        click.echo(
            f"{obj.name:<{name_w}}  {obj.type_name:<{type_w}}  {len(obj.raw):7d}  {crc_str:<4}  {mode_str}"
        )


@main.command()
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--name", "prog_name", default=None, help="Program name on calculator (defaults to file stem).")
@click.option(
    "--compress/--no-compress",
    default=None,
    help="Force zlib compression on or off (default: auto when payload > 800 bytes).",
)
@click.option("--verify", is_flag=True, help="Read back from calculator via 0xF9 to verify transfer.")
def send(filepath: Path, prog_name: str | None, compress: bool | None, verify: bool) -> None:
    """Send a PPL source file to the HP Prime G2."""
    name = prog_name or filepath.stem
    try:
        source = _read_source_file(filepath)
    except UnicodeDecodeError as exc:
        raise click.ClickException(f"Could not decode {filepath}: {exc}") from exc

    try:
        with HPPrimeG2() as calc:
            calc.connect()
            calc.send_ppl(name, source, compress=compress)
            if verify:
                objects = calc.list_objects()
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Sent program {name!r} ({len(source)} chars) from {filepath}.")
    if verify:
        matches = [o for o in objects if o.file_type == TYPE_PROGRAM and o.name == name]
        if not matches:
            raise click.ClickException(f"Verification failed: {name!r} not returned by calculator.")
        pulled = decode_ppl_source(matches[-1])
        expected = _normalize_source(source)
        if pulled != expected:
            raise click.ClickException(
                f"Verification failed: content mismatch for {name!r} "
                f"(sent {len(expected)} chars, read back {len(pulled)} chars)."
            )
        click.echo(f"Verified {name!r} on calculator (CRC={'OK' if matches[-1].crc_ok else 'FAIL'}).")


@main.command()
@click.argument("name")
@click.option("-o", "--output", "out_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
def pull(name: str, out_path: Path | None) -> None:
    """Pull a PPL program from the calculator to stdout or a file."""
    try:
        with HPPrimeG2() as calc:
            calc.connect()
            objects = calc.list_objects()
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    matches = [o for o in objects if o.file_type == TYPE_PROGRAM and o.name == name]
    if not matches:
        available = ", ".join(o.name for o in objects if o.file_type == TYPE_PROGRAM) or "(none)"
        raise click.ClickException(f"Program {name!r} not found. Available: {available}")

    source = decode_ppl_source(matches[-1])
    if out_path is not None:
        out_path.write_text(source, encoding="utf-8")
        click.echo(f"Saved {name!r} ({len(source)} chars) to {out_path}.")
    else:
        sys.stdout.write(source)
        if source and not source.endswith("\n"):
            sys.stdout.write("\n")


@main.command()
@click.argument("names", nargs=-1, required=True)
@click.option("--verify", is_flag=True, help="Read back object list via 0xF9 to confirm deletion.")
def delete(names: tuple[str, ...], verify: bool) -> None:
    """Delete one or more PPL programs from the calculator."""
    try:
        with HPPrimeG2() as calc:
            calc.connect()
            for name in names:
                calc.delete_ppl(name)
                click.echo(f"Deleted program {name!r}.")
            if verify:
                objects = calc.list_objects()
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if verify:
        remaining = {o.name for o in objects if o.file_type == TYPE_PROGRAM}
        still_present = [n for n in names if n in remaining]
        if still_present:
            raise click.ClickException(
                f"Verification failed: still present on calculator: {', '.join(still_present)}"
            )
        click.echo(f"Verified deletion of {', '.join(repr(n) for n in names)}.")
