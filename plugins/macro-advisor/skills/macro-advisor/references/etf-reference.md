# ETF Reference — Lookup Table

Consulted by the thesis generator (Skill 7) and Monday briefing (Skill 9) when they need ETF tickers. Collection skills (1-5) and synthesis (6) generally don't need this file.

> **Note:** Run `/macro-advisor:setup` to generate the currency-specific equivalents section (Layer 1) at the top of this file. Until setup runs, only USD tickers are available below.

---

## Broad Allocation ETFs (USD tickers)

- US Large Cap: **SPY** (SPDR S&P 500), **VOO** (Vanguard S&P 500), **IVV** (iShares Core S&P 500)
- US Large Cap Growth: **QQQ** (Invesco Nasdaq 100), **VUG** (Vanguard Growth)
- US Large Cap Value: **VTV** (Vanguard Value), **VOOV** (Vanguard S&P 500 Value)
- US Small Cap: **IWM** (iShares Russell 2000), **VB** (Vanguard Small-Cap)
- International Developed: **EFA** (iShares MSCI EAFE), **VEA** (Vanguard FTSE Developed), **IEFA** (iShares Core MSCI EAFE)
- Emerging Markets: **EEM** (iShares MSCI Emerging Markets), **VWO** (Vanguard FTSE Emerging Markets), **IEMG** (iShares Core MSCI EM)
- US Aggregate Bonds: **AGG** (iShares Core US Aggregate Bond), **BND** (Vanguard Total Bond Market)
- Long-Duration Treasury: **TLT** (iShares 20+ Year Treasury), **VGLT** (Vanguard Long-Term Treasury)
- Short-Duration Treasury: **SHV** (iShares Short Treasury), **BIL** (SPDR 1-3 Month T-Bill), **SGOV** (iShares 0-3 Month Treasury)
- TIPS (Inflation Protected): **TIP** (iShares TIPS Bond), **SCHP** (Schwab US TIPS)
- High Yield Corporate: **HYG** (iShares High Yield Corporate Bond), **JNK** (SPDR Bloomberg High Yield)
- Investment Grade Corporate: **LQD** (iShares Investment Grade Corporate Bond), **VCIT** (Vanguard Intermediate-Term Corporate)
- Gold: **GLD** (SPDR Gold Shares), **IAU** (iShares Gold Trust)
- Broad Commodities: **DJP** (iPath Bloomberg Commodity), **GSG** (iShares S&P GSCI Commodity)
- Oil: **USO** (United States Oil Fund), **BNO** (United States Brent Oil Fund)
- Real Estate: **VNQ** (Vanguard Real Estate), **SCHH** (Schwab US REIT)
- Cash Equivalent: **SGOV** (iShares 0-3 Month Treasury), **BIL** (SPDR 1-3 Month T-Bill)

---

## Thematic/Sector ETFs (USD tickers)

- Aerospace & Defense: **ITA** (iShares US Aerospace & Defense), **PPA** (Invesco Aerospace & Defense), **XAR** (SPDR S&P Aerospace & Defense)
- Robotics & Drones: **ARKQ** (ARK Autonomous Technology & Robotics), **ROBT** (First Trust Robotics & AI), **BOTZ** (Global X Robotics & AI)
- Cybersecurity: **CIBR** (First Trust NASDAQ Cybersecurity), **HACK** (ETFMG Prime Cyber Security), **BUG** (Global X Cybersecurity)
- Semiconductors: **SMH** (VanEck Semiconductor), **SOXX** (iShares Semiconductor)
- Energy (broad): **XLE** (Energy Select Sector SPDR), **VDE** (Vanguard Energy)
- Oil E&P: **XOP** (SPDR S&P Oil & Gas Exploration & Production)
- Clean Energy: **ICLN** (iShares Global Clean Energy), **TAN** (Invesco Solar)
- Uranium/Nuclear: **URA** (Global X Uranium), **URNM** (Sprott Uranium Miners), **NLR** (VanEck Uranium & Nuclear Energy)
- Biotech: **XBI** (SPDR S&P Biotech), **IBB** (iShares Biotech)
- Financials: **XLF** (Financial Select Sector SPDR), **KBE** (SPDR S&P Bank), **KRE** (SPDR S&P Regional Banking)
- Infrastructure: **PAVE** (Global X US Infrastructure Development)
- Space: **UFO** (Procure Space), **ARKX** (ARK Space Exploration & Innovation)
- China: **FXI** (iShares China Large-Cap), **KWEB** (KraneShares CSI China Internet), **MCHI** (iShares MSCI China)
- Japan: **EWJ** (iShares MSCI Japan), **DXJ** (WisdomTree Japan Hedged Equity)
- Europe: **VGK** (Vanguard FTSE Europe), **EZU** (iShares MSCI Eurozone)
- India: **INDA** (iShares MSCI India)
- Brazil: **EWZ** (iShares MSCI Brazil)
- Copper/Mining: **COPX** (Global X Copper Miners), **PICK** (iShares MSCI Global Metals & Mining)
- Lithium/Battery: **LIT** (Global X Lithium & Battery Tech)
- Rare Earth/Strategic Metals: **REMX** (VanEck Rare Earth/Strategic Metals)
- Agriculture: **DBA** (Invesco DB Agriculture)
- Water: **PHO** (Invesco Water Resources)
- Utilities (defensive): **XLU** (Utilities Select Sector SPDR)
- Healthcare (defensive): **XLV** (Health Care Select Sector SPDR)
- Consumer Staples (defensive): **XLP** (Consumer Staples Select Sector SPDR)

---

## Dynamic ETF Discovery

When a thesis needs exposure to a theme not covered above:

```bash
python scripts/etf_lookup.py --theme "drone warfare defense"
python scripts/etf_lookup.py --theme "space satellite"
python scripts/etf_lookup.py --verify "ARKQ,ITA,UFO"
```

Searches ~100 liquid ETFs, verifies real price data on Yahoo Finance, returns: ticker, name, price, 1M/3M performance, AUM. Only recommend ETFs the script has verified. If no match: "no verified ETF found for [theme] — manual research needed."
