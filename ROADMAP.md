# Roadmap

## V7.1 — Foundation

Status: documented and in use.

- Stable systemd service
- Local LLM editing and translation
- MQTT publication to AWTRIX
- Forced bulletin refresh by button
- Automatic clearing after the display window

## V7.2 — News Engine

Status: documented from the current development state.

- Shared news pool
- Ranking before bulletin creation
- Replay cache
- Persistent language selection
- Improved scheduling and logging

Remaining engine work:

- Enforce a maximum pool size
- Remove expired stories reliably
- Improve cross-source duplicate detection
- Add feed health statistics
- Move feeds and priorities into configuration files

## V7.3 — Global News

Status: current development branch.

Primary goal: expand coverage while keeping the AWTRIX bulletin concise and current.

Planned first source groups:

- World: BBC, France 24, Deutsche Welle, Al Jazeera, ABC Australia
- France: Le Monde/France feed, Les Echos and additional reliable French feeds
- Germany: Spiegel, Tagesschau and Deutsche Welle
- Technology and AI: Wired, Ars Technica, The Register and official AI project feeds
- Science and space: NASA, ESA and selected science publications
- Personal interests: energy, solar, Bitcoin/mining and Tesla

Selection principles:

- Prefer reliable feeds with stable RSS or Atom endpoints.
- Do not allow one source to dominate a bulletin.
- Merge reports about the same event.
- Prioritize current, consequential and personally relevant stories.
- Keep the final bulletin small enough for AWTRIX.

## V7.4 — Information Hub

- Currency, gold and Bitcoin tiles
- Weather and outdoor temperature
- Victron and solar status
- Avalon miner status
- Tesla status
- Shared display-priority rules for news and live data

## V8 — Personal Information Assistant

Long-term direction: a local system that selects the most useful information for the user and can publish it to AWTRIX and other interfaces.
