![Test and Build](https://github.com/bovheat/bovheat/workflows/Test%20and%20Build/badge.svg)
![Lint](https://github.com/bovheat/bovheat/workflows/Lint/badge.svg)
# BovHEAT

Bovine Heat Analysis Tool (BovHEAT) - Automated Heat detection and analysis tool for "SCR Heatime"
(SCR Engineers Ltd., Netanya, Israel) a neck-mounted accelerometer for automated activity monitoring in cows.
This tool analyses the raw data and performs error detection and correction. Additional data sources will be
supported in the future.

![Heat Example Image](docs/img/2020-05-15_heat_example_6.png)

## Usage
1. Download the executable corresponding to your OS from [excecutables/](excecutables/)
2. Put BovHEAT in the folder containing SCR XLSX and XLS data files.  
Alternatively you can group SCR files in folders and put BovHEAT in the parent folder.
3. Execute BovHEAT, wait for it to start and follow the onscreen instructions.

## Demo
Example XLSX and PDF output can be viewed at [data/example_output/](data/example_output/)

To generate the output for yourself, start BovHeat in the provided [sample data](data/) folder.

## Constraints
Cow IDs have to be unique in the data or unique within folders. 

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