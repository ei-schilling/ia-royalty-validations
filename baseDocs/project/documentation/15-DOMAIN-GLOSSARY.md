# 15 — Domain Glossary

## Overview

The Royalty Statement Validator works with data from the **Schilling ERP** system, a Danish publishing-industry royalty settlement platform. This glossary explains the domain-specific terminology, Danish field names, and business concepts.

---

## Core Concepts

### Royalty Statement (Royalty‌afregning)

A periodic document sent to an author/recipient detailing:
- Sales of their works during the period
- Calculated royalty amounts per channel/price group
- Deductions (guarantees, taxes, duties)
- Net payout amount

### Settlement (Afregning)

The process of calculating royalties owed to recipients for a given period. The Schilling system runs settlements in batches, processing all eligible agreements and producing statements.

### Agreement (Aftale)

A contract between a publisher and a recipient (author, agent, heir) defining:
- Which products (books) are covered
- Royalty rates per sales channel and price group
- Guarantee amounts
- Settlement frequency and currency

### Recipient / Author (Forfatter / Konto)

The person or entity receiving royalties. Can be:
- An author (forfatter)
- A literary agent
- An heir (arving)
- A co-author (medforfatter)

---

## Danish Field Names

### Transaction Fields (ROYPOST)

| Field | Danish Name | English | Description |
|-------|-------------|---------|-------------|
| `TRANSNR` | Transaktionsnummer | Transaction number | Unique identifier for each transaction |
| `TRANSTYPE` | Transaktionstype | Transaction type | One of ~40 types (Salg, Retur, Garanti, etc.) |
| `KONTO` | Konto | Account | Recipient/author account number |
| `AFTALE` | Aftale | Agreement | Agreement number linking product to recipient |
| `ARTNR` | Artikelnummer | Article number | Product identifier (often ISBN) |
| `KANAL` | Salgskanal | Sales channel | Distribution channel (DK, Online, Export, etc.) |
| `PRISGRUPPE` | Prisgruppe | Price group | Pricing tier for royalty calculation |
| `VILKAR` | Vilkår | Terms | Agreement terms code |
| `BILAGSNR` | Bilagsnummer | Voucher number | Reference number for the transaction |
| `BILAGSDATO` | Bilagsdato | Voucher date | Date of the transaction voucher |
| `ANTAL` | Antal | Quantity | Number of units (positive for sales, negative for returns) |
| `STKPRIS` | Stykpris | Unit price | Price per unit |
| `STKAFREGNSATS` | Stykafregningssats | Settlement unit rate | Royalty rate applied per unit (percentage as decimal) |
| `BELOEB` | Beløb | Amount | Calculated royalty amount |
| `VALUTA` | Valuta | Currency | Currency code (usually DKK) |
| `SKAT` | Skat | Tax | Tax withholding amount |
| `AFREGNBATCH` | Afregningsbatch | Settlement batch | Batch number (0 = unsettled, >0 = settled) |

### Statement Summary Fields

| Field | Danish | English | Description |
|-------|--------|---------|-------------|
| `fordeling` | Fordeling | Distribution | Total royalty before deductions |
| `fordeling_pct` | Fordelingsprocent | Distribution percentage | Author's share percentage |
| `rest_garanti` | Restgaranti | Remaining guarantee | Guarantee amount still to be recouped |
| `afgift` | Afgift | Duty/Levy | Social duty deduction |
| `til_udbetaling` | Til udbetaling | For payment | Net payout amount after all deductions |
| `primo_lager` | Primo lager | Opening stock | Beginning inventory count |
| `ultimo_lager` | Ultimo lager | Closing stock | Ending inventory count |

---

## Transaction Types

The Schilling system defines ~40 transaction types. These are the most common:

### Sales & Returns

| Type | Danish | English | Sign |
|------|--------|---------|------|
| `Salg` | Salg | Sales | + |
| `SalgTilb` | Salg tilbageført | Sales credit/return | - |
| `Returneret` | Returneret | Returns | - |
| `Svind` | Svind | Wastage/shrinkage | - |

### Financial

| Type | Danish | English | Sign |
|------|--------|---------|------|
| `Udbetalt` | Udbetalt | Paid out | - |
| `Skat` | Skat | Tax withheld | - |
| `Afgift` | Afgift | Social duties | - |
| `Moms` | Moms | VAT | - |
| `Pension` | Pension | Pension deduction | - |
| `Ambi` | AM-bidrag | Labour market contribution | - |

### Guarantees

| Type | Danish | English | Description |
|------|--------|---------|-------------|
| `GarLokal` | Garanti lokal | Local guarantee | Guarantee on a single agreement |
| `GarLokalMod` | Garanti lokal modpost | Local guarantee offset | Recoupment against local guarantee |
| `GarGlobal` | Garanti global | Global guarantee | Guarantee across linked agreements |
| `GarGlobalMod` | Garanti global modpost | Global guarantee offset | Recoupment against global guarantee |
| `GarMethod` | Garanti metode | Method guarantee | Method-based guarantee |
| `GarMethodMod` | Garanti metode modpost | Method guarantee offset | Recoupment against method guarantee |

### Advances & Adjustments

| Type | Danish | English | Description |
|------|--------|---------|-------------|
| `Forskud` | Forskud | Advance | Money paid to author in advance |
| `ForskudMod` | Forskud modpost | Advance offset | Deduction of advance from royalties |
| `Erstatning` | Erstatning | Compensation | One-time payment (e.g., rights purchase) |
| `AfregnjJust` | Afregningsjustering | Settlement adjustment | Manual correction to a settled amount |
| `EngangsHonorar` | Engangshonorar | One-off fee | Fee hidden from statement |

### Other

| Type | Danish | English | Description |
|------|--------|---------|-------------|
| `Oplag` | Oplag | Print run | Stock/inventory quantity |
| `Frieks` | Frieksemplarer | Free copies | Complimentary copies (no royalty) |
| `Antologi` | Antologi | Anthology | Anthology contribution royalty |
| `AntologiMod` | Antologi modpost | Anthology offset | Anthology offset |
| `ProdRoy` | Produktionsroyalty | Production royalty | Royalty on production |
| `ProdRoyArv` | Produktionsroyalty arv | Production royalty (inherited) | Inherited production royalty |
| `Rente` | Rente | Interest | Withheld interest on guarantee balance |
| `OvfBrutto` | Overført brutto | Gross carry-over | Balance adjustment |
| `GrossAmount` | Bruttobeløb | Gross amount | Pre-tax gross amount |

---

## Business Concepts

### Guarantee (Garanti)

An advance committed to an author that is recouped from earned royalties. Three scopes:

- **Local** (Lokal): Single agreement — the advance is recouped only from royalties on that agreement
- **Global**: Across linked agreements — recoupment can happen from royalties on any linked agreement
- **Method** (Metode): Based on a specific calculation method

A guarantee is "earned out" when cumulative royalties exceed the guarantee amount.

### Fordeling (Distribution)

The base royalty amount calculated from sales before any deductions. When there are co-authors, the fordeling is split according to their registered share percentages.

### Price Type (Pristype)

Determines which price is used as the basis for royalty calculation:

| Code | Meaning |
|------|---------|
| Forlagspris | Publisher's list price |
| Nettopris | Net price (after discount) |
| Vejledende forlagspris | Recommended publisher's price |
| Realisationspris | Remainder/clearance price |

### Staircase Rates (Trappesatser)

Tiered royalty rates that change based on cumulative sales:

```
0–2,000 copies:      10%
2,001–5,000 copies:  12%
5,001–10,000 copies: 15%
10,001+ copies:      18%
```

### Settlement Group (Afregningsgruppe)

Agreements are grouped into settlement groups that are processed together in a batch. This ensures all related agreements for a recipient are settled simultaneously.

### Co-Author Shares (Medforfatteroller)

Multiple recipients can share royalties on a work. Distribution methods:

| Method | Description |
|--------|-------------|
| Percentage | Fixed percentage per recipient |
| Points | Shares calculated from allocated points |
| Pages | Shares calculated from page contribution |

### DKK (Danish Krone)

The primary currency used in Danish publishing royalty calculations. The system supports multi-currency, but DKK is the default.

---

## Schilling ERP Context

### What is Schilling?

Schilling is a comprehensive ERP system for the Danish publishing industry, built in C++ with Oracle SQL. The royalty module handles:

- Agreement management
- Transaction import & coupling
- Settlement calculation
- Tax & duty withholding
- Statement generation
- Financial posting

### Relationship to This Validator

This validator does **not** connect to Schilling or its Oracle database. It validates **exported files** (CSV, Excel, JSON, PDF) against the same business rules that Schilling enforces. Think of it as an independent quality check on Schilling's output.

### Common Schilling Number Format

| Danish | English | Note |
|--------|---------|------|
| `70.470,00` | `70,470.00` | Period = thousands separator, comma = decimal |
| `-500,00` | `-500.00` | Negative with leading minus |
| `=10/100` | `0.10` | Excel formula in CSV exports (10%) |
| `=15/100` | `0.15` | Excel formula (15%) |
