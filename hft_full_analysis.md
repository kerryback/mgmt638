High‑frequency trading (HFT) is basically “microstructure trading with a physics problem attached”: algorithms compete over microseconds to win tiny edges in limit order books.

I’ll walk through:

1. What HFT actually is  
2. Common strategy families  
3. How HFT firms make money (and how concentrated those profits are)  
4. Colocation, networks, and computing stack  
5. “Sniping” in Budish–Cramton–Shim and why they think the market design is broken  

---

## 1. What is high‑frequency trading?

High‑frequency trading is a subset of algorithmic trading characterized by:

- **Very short holding periods** – positions often last milliseconds to minutes.  
- **Huge message traffic** – constant stream of quotes, cancels, and small trades.  
- **Latency minimization** – heavy investment in colocation, custom networks, and specialized hardware to shave microseconds.  
- **Proprietary strategies** – mostly proprietary (prop) trading rather than agency flow.

Regulators and surveys typically classify “HFT” as firms that:

- Use **automated order placement and cancellation** at very high frequency,  
- Maintain **very low intraday inventory** (they rarely carry large overnight positions), and  
- Are often **co‑located** at exchanges and account for a large share of order messages, even if a smaller share of volume.citeturn2search11turn0search9  

As of the mid‑2010s, HFT was estimated to account for roughly **10–40% of equity trading volume**, and a significant share of FX and futures volume, though the exact share varies by asset class and venue.citeturn2search11turn0search9  

---

## 2. Common HFT strategy families

### 2.1 Market‑making / liquidity provision

These HFTs are “electronic specialists”:

- They continuously **post bid and ask quotes** around a model of fair value.  
- They adjust spreads and size based on volatility, order flow, and inventory.  
- They earn the **bid–ask spread** (and often exchange liquidity rebates) when filled.

Academic and industry studies find:

- Many HFTs specialize in market‑making, and their presence is associated with **tighter spreads and greater depth** on average.citeturn0search9turn0search23  
- HFT liquidity provision is especially important in large‑cap equities and major futures, and many HFT market makers increase liquidity in volatile periods rather than withdraw.citeturn0search5turn0search23  

However, market‑making HFTs face **adverse selection**: the risk of being “run over” by informed or faster traders (this is where sniping will come in later).

---

### 2.2 Statistical arbitrage & relative‑value trading

This is the “small mispricing” game:

- **Pairs/stat arb:** trade correlated securities that temporarily deviate from historical relationships (e.g., dual‑listed stocks, ETF vs basket, ADR vs underlying).citeturn0search3turn0search15  
- **Index vs constituent / ETF vs futures:** exploit basis errors between index futures (e.g., E‑mini S&P 500) and the ETF (SPY), or ETF vs its underlying basket.  
- **Cross‑asset relationships:** e.g., oil futures vs energy ETFs; foreign index futures vs currency‑hedged ETFs.citeturn6view0  

At high frequency, these are often **“mechanical” arbitrages**:  
public prices in one venue move; related prices elsewhere lag by a few milliseconds; the fastest trader arbitrages before others update.

Budish–Cramton–Shim’s ES‑SPY example (E‑mini S&P futures vs SPY ETF) is the canonical case: the faster trader races to trade against stale SPY quotes when the futures price jumps.citeturn2search4  

---

### 2.3 Event / news trading

HFTs also compete on **news latency**:

- Direct feeds from newswires, economic calendars, and proprietary “machine‑readable news” let them parse macro announcements within microseconds.  
- Typical targets: **Fed announcements, payrolls, CPI, earnings releases, index rebalances**.  
- Strategy: re‑price limit orders and hit/offer liquidity the moment their model detects a surprise.

Empirical work finds that **low‑latency traders earn significant rents around macro announcements**, mainly by being first to reprice, and that these profits are strongly related to speed.citeturn3search8turn3search0  

---

### 2.4 Latency arbitrage & queue‑positioning

“Latency arb” is broader than just stat arb:

- **Cross‑venue price dislocations:** The same stock trading on multiple exchanges with slightly different prices. The fastest HFT can buy where it’s cheap and sell where it’s expensive, or arbitrage against slower smart‑order routers.citeturn2search11turn0search24  
- **Queue‑position games:** With price‑time priority, being first at a given price is valuable. HFTs constantly cancel/repost to **improve queue rank**, so they get filled before rivals when liquidity arrives. The minimum tick size and maker‑taker fees amplify this race.citeturn6view0turn0search23  

Aquilina–Budish–O’Neill (2022 / BIS WP 955) document “**races**”: bursts where multiple firms simultaneously try to hit or cancel at the same price. They find:

- ~**500+ races per day** in FTSE‑100 stocks  
- Typical race length ≈ **tens of microseconds**  
- Over **20% of volume** occurs inside such races  
- The implied cost to slower participants is on the order of **$5bn/year** globally – essentially a latency‑arb “tax” on trading.citeturn0search24turn1view0  

This is exactly the sort of behavior Budish–Cramton–Shim label **sniping**.

---

### 2.5 Liquidity detection / order anticipation

Some strategies are about **reading large institutional flow**:

- Algorithms analyze order‑book patterns, child order slices, and venue usage to infer the presence of a large parent order being worked over time.  
- Tactics include sending small “ping” orders, reacting to partial fills, and exploiting predictable routing patterns.

When successful, an HFT might buy just ahead of a big buy program and sell back to it slightly higher (or vice versa), capturing a small edge from anticipating the order.citeturn0search0turn0search26turn0search29  

These strategies are controversial because they can **raise execution costs** for large, slower traders.

---

### 2.6 Rebate / fee, microstructure, and routing arbitrage

Other, more niche activities:

- **Maker–taker fee arbitrage:** Posting liquidity on venues that pay higher rebates while routing marketable orders to cheaper venues, subject to best‑execution.citeturn0search24  
- **Hidden / midpoint venues:** Rapidly arbitraging between lit markets and dark or midpoint books.  
- **Specialist products:** E.g., trading exchange‑listed volatility products, fragmented options markets, or off‑the‑run vs on‑the‑run bonds using microstructure quirks.

---

## 3. How HFT firms actually earn profits

### 3.1 Revenue channels

In a simplified way, HFT P&L decomposes into:

1. **Spread capture**  
   - Market‑making strategies earn **half the bid–ask spread** per roundtrip (less adverse selection).  
   - In many markets, maker rebates add a few mils per share, which can be substantial at HFT volumes.citeturn0search9turn0search23  

2. **Arbitrage profits**  
   - Profits from cross‑venue, cross‑asset, and latency arbitrage – buying low / selling high on very small mispricings that others can’t reach fast enough.citeturn6view0turn4search11turn0search24  

3. **Short‑horizon informational edge**  
   - By crunching order‑book and trade data, HFTs can often predict **the next few price changes** with better than 50% accuracy.  
   - Baron et al. find that faster HFTs achieve substantially better performance, and that speed helps both “short‑lived information” trading and risk management (faster position flattening).citeturn3search3turn3search8  

4. **Rebates / liquidity incentives**  
   - Exchanges compete for order flow by paying rebates or offering incentives for designated market makers. HFTs design strategies that **maximize rebate capture per unit of inventory risk**.

### 3.2 Empirical profitability & concentration

Key results from “Risk and Return in High‑Frequency Trading” (Baron, Brogaard, Hagströmer, Kirilenko):citeturn3search3turn3search8  

- Using data on E‑mini S&P futures, they show **profits are highly concentrated** in a small number of HFT firms.  
- The median HFT has very high risk‑adjusted returns (Sharpe > 4) but the **top firms earn the lion’s share of total profits**.  
- Firms that **improve their latency rank (e.g., via colocation upgrades)** experience improved trading performance, confirming that speed is a key competitive dimension.  
- Both **liquidity‑taking and liquidity‑providing** HFTs can be profitable, but the best firms tend to do both.

Aquilina–Budish–O’Neill’s race analysis implies that a sizeable chunk of these profits can be interpreted as **latency arbitrage rents**, effectively paid by slower traders and liquidity providers through worse execution or increased spreads.citeturn0search24turn1view0  

---

## 4. Colocation, networks, and computing stack

### 4.1 Colocation at exchanges

**Colocation** means renting rack space **inside (or immediately adjacent to)** the exchange’s data center:

- The HFT’s servers sit in the same building as the exchange’s matching engine.  
- They buy **cross‑connects** (short fiber runs) to the exchange gateways and proprietary data feeds.  
- Exchanges usually ensure all racks are **equalized cable distance** from the matching engine so competition is about *code and hardware*, not which firm’s rack is physically closer.citeturn0search13turn6view0  

Major equity and futures venues have dedicated colo sites, e.g.:

- **NYSE** in Mahwah, NJ  
- **Nasdaq** in Carteret, NJ  
- **Cboe / BATS / IEX and others** around Secaucus / NY4 in NJ  
- **CME** (futures) in Aurora, ILciteturn0search7turn4search22  

Empirically, “Trading Fast and Slow: Colocation and Liquidity” (Brogaard et al.) studies an optional speed upgrade at Nasdaq OMX Stockholm and finds:citeturn4search8turn4search12  

- Participants that upgraded were mainly **market‑makers**,  
- **Market liquidity improved** for both upgraded (fast) and non‑upgraded (slow) traders,  
- Suggesting that colocation can improve book quality even while creating a speed hierarchy.

---

### 4.2 Long‑distance low‑latency networks

For cross‑market strategies (e.g., CME Aurora ↔ NY equity exchanges in NJ), latency is dominated by **speed of light** constraints.

Key technologies:

- **Latency‑optimized fiber**: straightest routes, low‑refractive‑index fiber (e.g., Spread Networks’ Chicago–NY cable).  
- **Microwave / millimeter‑wave / free‑space optical links**: signals in air travel **faster than in fiber**, and the path can be closer to geodesic, so they beat the best fiber routes by ~30–40%.citeturn2search11turn4search11  

Concrete numbers:

- NASDAQ–CME official microwave service advertises being up to **36% faster** than the best fiber paths on the same corridor.citeturn0search25  
- Quincy Data + McKay Brothers report one‑way microwave latency from CME Aurora to NJ data centers of about **3.98–4.02 ms** rack‑to‑rack (Aurora→Carteret/Mahwah/NY2).citeturn4search2turn4search10turn4search9  
- Earlier generations of microwave routes had ~**8 ms round‑trip** (≈4 ms one‑way), which have been upgraded over time.citeturn4search1turn4search5turn4search24  
- Indepen­dent network‑measurement work shows the fastest CME↔NY4 paths around **3.96 ms one‑way** as of 2020, very close to the physical speed‑of‑light limit.citeturn4search22turn4search11  

Laughlin–Aguirre–Grundfest estimate that building these Chicago–NJ low‑latency links (fiber + microwave) cost **hundreds of millions of dollars** collectively and that there are dozens of overlapping private microwave networks on the corridor.citeturn4search11turn4search18  

This is the **arms race in hardware** that Budish et al. are reacting to.

---

### 4.3 Computing architecture

Typical on‑exchange HFT stack (simplified):

- **Bare‑metal servers**, not cloud, to minimize jitter.  
- **Kernel‑bypass NICs** (e.g. Solarflare/Onload, DPDK) and tuned OS stacks (Linux with custom NIC drivers, IRQ pinning, disabled power‑saving, etc.) to reduce and stabilize latency.citeturn0search27  
- **FPGAs or specialized network appliances** for ultra‑low‑latency market data decoding and order‑entry; sometimes full strategies run in hardware.citeturn0search27turn0search13  
- Production strategies written in low‑level languages (C/C++/Rust), with careful control of memory allocation and branch prediction.  
- **Time synchronization** via GPS and PTP to keep nanosecond‑level timestamps aligned between servers.  
- Extensive **risk‑checks and kill‑switches** at multiple levels: firm‑side pre‑trade risk controls, exchange risk gateways, and regulatory limits.

For **research/backtesting**, HFTs are more willing to use conventional data centers or cloud: large clusters to process full depth‑of‑book history, train models, etc. Cutting‑edge ML / reinforcement learning is increasingly used for signal discovery, but in production these models still have to obey strict latency budgets.citeturn0search27turn0search1  

---

### 4.4 Third‑party services

HFTs rely on a small ecosystem of specialized vendors:

- **Microwave / low‑latency data vendors:** McKay Brothers, Quincy Data, New Line Networks, and others provide turnkey **“fastest known” routes** and normalized market data across multiple venues.citeturn4search9turn4search17turn4search20  
- **Exchange‑run low‑latency products:** e.g., NASDAQ–CME microwave, or (more recently controversial) hollow‑core fiber offerings.citeturn0search25turn4news42  
- **Colocation & connectivity resellers:** firms that manage cages, cross‑connects, and remote hands for trading firms.

---

## 5. “Sniping” in Budish–Cramton–Shim (Budish–Cramton–Shim)

The user said “Budish, Cramton, and Shin,” but the classic paper is **Budish, Cramton, and Shim**:  
*“The High‑Frequency Trading Arms Race: Frequent Batch Auctions as a Market Design Response”* (QJE 2015).citeturn2search0turn2search5  

### 5.1 Their core argument

BCS make three main points:

1. The **continuous limit order book (CLOB)** doesn’t “work” in continuous time at microsecond horizons: measured correlations between closely related instruments (e.g., ES futures and SPY ETF) break down when you look at millisecond data, even though they’re almost perfectly correlated at coarser horizons.citeturn2search0turn6view0  
2. This breakdown creates **“obvious mechanical arbitrage opportunities”** – not about private information, but about **who is fastest to act on public information**.  
3. Competition doesn’t eliminate these arbitrage profits; it just **drives an arms race for speed**, with social resources burned on ever‑faster networks and hardware.

They call the key exploit **sniping**.

---

### 5.2 What is “sniping” in their model?

BCS build a stylized model to capture what they see in the data.citeturn6view0turn2search4  

Set‑up (simplified):

- A security \(x\) trades on a continuous limit order book with price‑time priority.  
- There is a **public signal \(y\)** (think E‑mini futures or public news) that perfectly tracks the fundamental value of \(x\).  
- Everyone can observe \(y\), but with a delay: **slow** traders see it with delay \(\delta_{	ext{slow}}\); **fast** traders can pay for technology to see it with delay \(\delta_{	ext{fast}} < \delta_{	ext{slow}}\).  
- There are **investors** (liquidity takers) and **market makers** (HFTs). Market makers can be either:
  - the **liquidity provider** posting tight quotes, or  
  - **stale‑quote snipers** who try to pick off those quotes when \(y\) jumps.

Mechanics of sniping:

1. The liquidity‑providing HFT posts quotes at \(y - s/2\) (bid) and \(y + s/2\) (ask), earning the spread \(s\) from investor trades.citeturn6view0  
2. Suddenly, the signal \(y\) jumps (say, the ES futures price moves up). Fundamental value rises.  
3. Because fast traders see the jump first, they can **immediately send aggressive orders** to hit the now‑stale ask (still at the old lower price), while the liquidity provider simultaneously tries to cancel those quotes.  
4. The exchange processes all these messages **serially**, in arrival order, but if they hit the exchange “at the same time” from colocated racks, tie‑breaking is effectively random.citeturn6view0  
5. A “sniper” wins the race with probability \(1/N\) (if there are \(N-1\) snipers plus 1 liquidity provider racing). If they win, they:
   - **Buy at the stale ask** (too low given the new \(y\)),  
   - Immediately **resell at or near the new fair value**, locking in a mechanical profit.  
   - Symmetrically for downward jumps and stale bids.

BCS label these “**stale‑quote snipers**” and explicitly note that many real‑world HFT firms temporarily play both roles: sometimes providing liquidity, sometimes sniping others’ stale quotes.citeturn6view0turn2search3  

Economically, sniping is:

- **Not about private information** – everyone sees the same public signal, just with tiny latency differences.  
- A straightforward consequence of **continuous‑time, serial order processing**: if you allow continuous submissions and price‑time priority, and everyone sees a public jump with small latency differences, someone will always be “too slow” and vulnerable to being picked off.

---

### 5.3 Consequences: spreads and the arms race

BCS derive an equilibrium where:

- The liquidity provider’s **expected profit from spreads** (trades with investors) must compensate for **expected losses to snipers** plus the cost of speed technology.  
- As more snipers enter and/or speed gets more expensive, **spreads widen** to keep market makers at zero economic profit.citeturn6view0turn2search4  
- The sniping game is a **prisoner’s dilemma**: each firm must invest in speed to avoid being picked off, but collectively they just re‑divide the same arbitrage rents while burning real resources (microwave links, hardware, engineers).

Their empirical extrapolation from ES‑SPY opportunities suggests the total “prize” from latency arb is on the order of **billions of dollars per year**, consistent with later Aquilina–Budish–O’Neill estimates.citeturn6view0turn0search24  

---

### 5.4 Frequent Batch Auctions as a fix

BCS propose a radical design change: **Frequent Batch Auctions (FBA)**.citeturn2search0turn2search4turn2search3  

Key features:

- Instead of processing orders continuously, the exchange runs a **uniform‑price double auction every \(	au\) seconds** (e.g., every 100ms or 1s).  
- All orders arriving during an interval are batched and cleared at once at a single price; **within a batch, time priority disappears**, only price priority matters.  
- Everyone still sees public information with different latencies, but as long as they react **within the same batch**, being microseconds faster yields almost no advantage.

In their model:

- **Sniping disappears**: fast traders no longer earn rents by beating a cancel by microseconds, because execution is determined at the batch auction based on prices, not nanosecond timestamps (their Proposition 8).citeturn2search4  
- **Liquidity improves**: because market makers are no longer constantly being picked off, they can quote tighter spreads and deeper size.  
- The **arms race for sub‑millisecond speed largely stops**: there’s still value to being reasonably fast (to get orders into the current batch), but not from shaving nanoseconds.

In other words, BCS argue that **sniping is not a natural or necessary byproduct of electronic trading**, but a *market‑design choice* (continuous, serial limit order books with time priority). Switch the design, and you dramatically reduce the incentive to build $500m worth of microwave towers for a few microseconds of edge.

---

## 6. Putting it together

If you step back:

- **“Good” HFT**: market‑making and some statistical arb tighten spreads, deepen liquidity, and keep prices aligned across venues and instruments.  
- **“Problematic” HFT**: sniping/latency arb and aggressive order‑anticipation strategies can act like a **tax on slower traders**, with profits largely reflecting speed rents rather than new information.  
- The **infrastructure** (colocation, microwave, FPGAs) is both the enabler of HFT profits and the source of social concern: the arms race is expensive, and much of the private benefit is a transfer from slower traders.

Budish–Cramton–Shim’s sniping framework is useful because it sharpens the distinction between:

- **Traditional informed trading** (compensated for discovering information), versus  
- **Latency arbitrage / sniping** (compensated for being slightly faster to react to the *same* information).

That distinction helps think about which forms of HFT we might want markets to encourage, and which might be better addressed via design changes (batch auctions, speed bumps, randomized delays) or regulation.
