# FR0333 Census Black Detailed Origin 0001

## Purpose

This rail preserves the distinction between the federal **Black or African American** umbrella category and the detailed identity **African American** while retaining detailed Caribbean and Sub-Saharan African origin counts.

Canonical metric:

`FR0333.CENSUS.BLACK.DETAILED.ORIGIN.0001`

Golden Chain link:

`FR.0333.GOLDEN.CHAIN.CENSUS.BLACK.DETAILED.ORIGIN.0001`

## Control law

`BLACK.OR.AFRICAN.AMERICAN != AFRICAN.AMERICAN`

`RACE != NATIONALITY != CITIZENSHIP != ANCESTRY != LANGUAGE`

`ECONOMIC.CONTRIBUTION != CLASSIFICATION.QUALIFIER`

`OBSERVED != CORRELATED != CAUSAL`

## 2020 DHC-A reference rail

The primary 2020 rail uses **alone or in any combination** detailed counts. The first reference point is African American at 24,569,479 persons. Jamaican, Haitian, Nigerian, Ethiopian, Somali, Trinidadian and Tobagonian, Ghanaian, Congolese, Kenyan, South African, Cameroonian, Liberian, and Eritrean follow as separate detailed identities.

Derived comparison uses **persons per 1000 African American reference**, not percentages.

## U.S. Virgin Islands rail

The U.S. Virgin Islands is held as a separate Island Areas geography. The rail stores total population, Black alone, Black alone or in combination, African American alone, U.S. Virgin Islander alone, and U.S. Virgin Islander alone or in any combination.

The U.S. Virgin Islands is not treated as a foreign sovereign-country category.

## 2024 ACS rail

The 2024 ACS B02023 values are stored as a separate **Black alone** estimate rail. The metric explicitly blocks an unqualified 2020-to-2024 growth delta because the 2020 DHC-A rail here uses alone-or-in-any-combination counts and the ACS rail uses Black-alone estimates.

## Genius Bar

The validator runs ten gates:

1. Identifier lock
2. Umbrella/detail separation
3. Questionnaire example lock
4. Source authority lock
5. DHC-A count rail lock
6. Reference ratio reconstruction
7. USVI geography lock
8. ACS universe separation
9. Classification boundary lock
10. Golden Chain promotion lock

Control invariant:

`TEN.IN -> TEN.OUT`

Promotion requires `10/10 PASS` and HumanLock remains active.

## Run locally

```bash
cd RavenCloudTaskbar
python3 fr0333_census_black_detailed_origin_genius.py
python3 test_fr0333_census_black_detailed_origin_genius.py
```

## Inventory and index

- `fr0333_golden_chain_inventory_0001.json`
- `fr0333_golden_chain_index_0001.json`

The Golden Chain index is append-only. Existing entries are not renumbered.

## Evidence boundary

This module records Census classifications and counts. It does not infer citizenship, nationality, language, lineage, causation, or economic worth from a race-category response. Economic contribution can be studied in a separate metric rail but is not a qualification for Census classification.
