# DATAQUEST Demo Script

## 0:00 to 0:20  Problem

“Personal data can appear across CSV files and SQL tables under different field names. DATAQUEST creates a reviewable local inventory and checks whether declared purpose and retention evidence exists.”

Show the Local processing indicator. State that the demo uses fictional data and no external AI.

## 0:20 to 0:50  Sources

Select **Load synthetic demo workspace**. Open Sources and show `admissions.csv`, `events.csv`, and `support.db`.

## 0:50 to 1:30  Discovery

Open Inventory. Select `guardian_phone`, `Phone Data Detected`, and `mobile`. Point out location, alias evidence, match count, strength label, masked sample, and rule version. Explain that rule strength describes evidence, not probability.

## 1:30 to 2:10  Footprint

Open Footprint. Show the same masked phone-like value in three source locations. Say: “This is an equal normalized value under the configured PHONE rule. It is a potential overlap, not proof of identity.”

## 2:10 to 2:45  Evidence gaps

Open Metadata. Show the events phone declaration with retention but no purpose. Show the support mobile declaration with purpose but no retention. Explain that DATAQUEST records declared evidence and does not judge legal sufficiency.

## 2:45 to 3:20  Human review

Open Review. Accept one finding with a short note. Mark another Review later. Explain that every decision appends a timestamped event and preserves earlier decisions.

## 3:20 to 4:00  Evaluation

Open Evaluation and run the included manual labels. Show per-class TP, FP, FN, TN, precision, recall, and support. State that the labelled set is small and synthetic.

## 4:00 to 4:30  Report

Open Reports and download the Markdown report or inventory CSV. Point out that the export contains masked samples and excludes raw values and fingerprints.

Close with: “DATAQUEST discovers potential personal-data fields, traces their footprint, connects them to declared purpose and retention evidence, explains each flag, and keeps uncertain cases open for human review.”

