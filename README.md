# Sniffr 🐶


**Sniffr** is a crypto safety tool designed to protect the Solana community by providing automated token risk analysis, community-driven reputation scoring, and crowdsourced intelligence. It integrates with social platforms like Twitter, leverages RugCheck’s API, and empowers users to vote on token safety and report suspicious activity.

---

## ✨ Key Features

### 1. Social Media Integration

#### Twitter Bot
- Listens for mentions and responds with token risk reports and wallet holdings.
- Supports commands:
  - `suspicious {wallet_address} with this token {token_address}` to analyze wallet holdings and token risks.
- Fetches data from RugCheck’s `/report/summary` API.
- Generates risk report image with:
  - Color-coded risk score ring.
  - Risk level and top 3 risks.
  - Sniffr watermark and disclaimer.
- Analyzes wallet holdings using RugCheck's `/insiders/graph` API.
- Example:
  - "Wallet AiksyB...cGTz holds 12345.67 tokens (participant). Here’s the token risk report: [image]"

#### Voting Support
- Users can upvote/downvote tokens via tweets:
  - `vote up {token_address}` or `vote down {token_address}`

---

### 2. Token Reputation System

#### Community Voting
- Vote submission to RugCheck via `/vote` endpoint.
- Example:
  - "Vote recorded for token EPjFWd...TDt1v! Upvotes: 10, Downvotes: 5, User voted: Yes"

---

### 3. Crowdsourced Intelligence

#### Insider Graph Analysis
- Uses `/insiders/graph` to report wallet holdings and network participation.

#### Suspicious Token Reporting
- Backend support via `/report` endpoint (implemented).
- Command trigger (e.g., `report token {token_address}`) is planned.

---

### Acknowledgements 
 - Rugcheck with robust API to meet developers demands.
