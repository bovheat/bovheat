![Test and Build](https://github.com/bovheat/bovheat/workflows/Test%20and%20Build/badge.svg)
![Lint](https://github.com/bovheat/bovheat/workflows/Lint/badge.svg)
# BovHEAT

Bovine Heat Analysis Tool (BovHEAT) - Automated Heat detection and analysis tool for "SCR Heatime"
(SCR Engineers Ltd., Netanya, Israel) a neck-mounted accelerometer for automated activity monitoring in cows.
This tool analyses the raw data and performs error detection and correction. Additional data sources will be
supported in the future.

![Heat Example Image](docs/img/2020-05-15_heat_example_6.png)

## Usage

## How to cite

## Development
To setup the development environment install [poetry](https://python-poetry.org/). And run:
```
poetry install
```

Start the programm:
```
poetry run python bovheat_src/bovheat.py
```

### Optional/Extras
To install packages related to testing:
```
poetry install -E pytest-testing
```
Linting:
```
poetry install -E pylint
```