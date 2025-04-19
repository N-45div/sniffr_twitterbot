import requests
import json
import tweepy
import logging
import re
import time
import infoimage
import credentials
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("twitter_bot.log"),
        logging.StreamHandler()
    ]
)

def get_tokenreport(token: str):
    URL = f"https://api.rugcheck.xyz/v1/tokens/{token}/report/summary"
    try:
        response = requests.get(URL)
        response.raise_for_status()
        res = json.loads(response.text)
        token_program = res.get("tokenProgram", "")
        risks = res.get("risks", [])
        overall_score = res.get("score", 0)
        normalized_score = res.get("score_normalised", 0)
        if not risks or normalized_score == 0:
            logging.warning(f"No valid risk data for token {token}: {res}")
            return None
        result = {
            "token_program": token_program,
            "risks": risks,
            "overall_score": overall_score,
            "normalized_score": normalized_score
        }
        return result
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            logging.error(f"Bad Request for token {token}: {response.text}")
            return None
        elif response.status_code == 404:
            logging.error(f"Token {token} not found: {response.text}")
            return None
        elif response.status_code == 429:
            logging.warning(f"Rate limit exceeded for RugCheck API")
            return None
        else:
            logging.error(f"HTTP error for token {token}: {e}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while calling API: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response: {e}")
        return None

def vote_token(token_address: str, side: bool):
    """Submit a vote (up or down) for a token mint address via RugCheck API."""
    URL = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/vote"
    headers = {
        "Authorization": f"Bearer {credentials.RUGCHECK_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "mint": token_address,
        "side": side  # true for upvote, false for downvote
    }
    
    try:
        response = requests.post(URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        logging.info(f"Successfully voted on token {token_address}: {result}")
        return {
            "success": True,
            "data": {
                "up": result.get("up", 0),
                "down": result.get("down", 0),
                "userVoted": result.get("userVoted", False)
            }
        }
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            logging.error(f"Invalid parameters for vote on {token_address}: {response.text}")
            return {"success": False, "message": f"Invalid parameters: {response.text}"}
        elif response.status_code == 401:
            logging.error(f"Unauthorized vote on {token_address}: {response.text}")
            return {"success": False, "message": "Unauthorized: Invalid API key"}
        elif response.status_code == 429:
            logging.warning(f"Rate limit exceeded for RugCheck API vote on {token_address}")
            return {"success": False, "message": "Rate limit exceeded"}
        else:
            logging.error(f"HTTP error voting on {token_address}: {e}")
            return {"success": False, "message": f"Failed to vote: {str(e)}"}
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error voting on {token_address}: {e}")
        return {"success": False, "message": "Network error"}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response for vote: {e}")
        return {"success": False, "message": "Invalid response format"}

def extract_token_address(text):
    token_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    token_matches = re.findall(token_pattern, text)
    return token_matches[-1] if token_matches else None

def extract_wallet_and_token(text):
    """Extract wallet address and token address from 'suspicious <wallet> with this token <token>' pattern."""
    pattern = r'suspicious\s+([1-9A-HJ-NP-Za-km-z]{32,44})\s+with\s+this\s+token\s+([1-9A-HJ-NP-Za-km-z]{32,44})'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)  # (wallet_address, token_address)
    return None, None

def extract_vote_request(text):
    """Extract token address and vote direction (up or down) from tweet text."""
    text_lower = text.lower()
    token_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    token_matches = re.findall(token_pattern, text)
    token_address = token_matches[-1] if token_matches else None
    
    if not token_address:
        return None, None
    
    if "vote up" in text_lower or "upvote" in text_lower:
        return token_address, True
    elif "vote down" in text_lower or "downvote" in text_lower:
        return token_address, False
    return None, None

def create_report_text(report, token_address):
    risk_text = ""
    for idx, risk in enumerate(report["risks"][:3]):
        risk_text += f"{idx+1}. {risk['name']}: {risk['level'].upper()}"
        if risk['value']:
            risk_text += f" ({risk['value']})"
        risk_text += "\n"
    
    score = report["normalized_score"]
    risk_level = "HIGH RISK" if score > 66 else "MEDIUM RISK" if score > 33 else "LOW RISK"
    
    text = (f"Token: {token_address[:6]}...{token_address[-4:]}\n"
            f"Risk Score: {score}/100 ({risk_level})\n\n"
            f"Top Risks:\n{risk_text}")
    
    return text

def get_insider_graph(token_address):
    """Fetch insider graph data for a token from RugCheck API."""
    URL = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/insiders/graph"
    headers = {
        "Authorization": f"Bearer {credentials.RUGCHECK_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        graph_data = response.json()
        logging.info(f"Successfully fetched insider graph for {token_address}")
        return {"success": True, "data": graph_data}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            logging.error(f"Unauthorized: Invalid RugCheck API key for token {token_address}")
            return {"success": False, "message": "Invalid API key"}
        elif response.status_code == 429:
            logging.warning(f"Rate limit exceeded for RugCheck API")
            return {"success": False, "message": "Rate limit exceeded"}
        else:
            logging.error(f"HTTP error fetching insider graph {token_address}: {e}")
            return {"success": False, "message": f"Failed to fetch graph: {str(e)}"}
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error fetching insider graph {token_address}: {e}")
        return {"success": False, "message": "Network error"}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response: {e}")
        return {"success": False, "message": "Invalid response format"}

def check_wallet_holdings(wallet_address, graph_data):
    """Check the holdings of a wallet address in the insider graph."""
    for network in graph_data:
        for node in network.get("nodes", []):
            if node.get("id") == wallet_address:
                holdings = node.get("holdings", 0)
                return {
                    "found": True,
                    "holdings": holdings,
                    "participant": node.get("participant", False)
                }
    return {"found": False, "holdings": 0, "participant": False}

def report_token(token_address):
    """Report a suspicious token to RugCheck API."""
    URL = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
    headers = {
        "Authorization": f"Bearer {credentials.RUGCHECK_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(URL, headers=headers)
        response.raise_for_status()
        result = response.json()
        logging.info(f"Successfully reported token {token_address}: {result}")
        return {"success": True, "message": "Token reported successfully"}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            logging.error(f"Unauthorized: Invalid RugCheck API key for token {token_address}")
            return {"success": False, "message": "Failed to report token: Invalid API key"}
        elif response.status_code == 429:
            logging.warning(f"Rate limit exceeded for RugCheck API")
            return {"success": False, "message": "Failed to report token: Rate limit exceeded"}
        else:
            logging.error(f"HTTP error reporting token {token_address}: {e}")
            return {"success": False, "message": f"Failed to report token: {str(e)}"}
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error reporting token {token_address}: {e}")
        return {"success": False, "message": "Failed to report token: Network error"}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response: {e}")
        return {"success": False, "message": "Failed to report token: Invalid response format"}

def respondToTweet(last_id):
    logging.info(f"Checking for mentions since ID: {last_id}")
    
    try:
        my_user_id = client.get_me().data.id
        logging.info(f"My user ID: {my_user_id}")
        
        kwargs = {
            "max_results": 10,
            "tweet_fields": ['text', 'created_at', 'author_id'],
            "expansions": ['author_id'],
            "user_fields": ['username']
        }
        
        if last_id != 1:
            kwargs["since_id"] = last_id
            
        mentions = client.get_users_mentions(my_user_id, **kwargs)
        
        if not mentions.data:
            logging.info("No new mentions found")
            return last_id
        
        logging.info(f"Found {len(mentions.data)} new mentions")
        newest_id = last_id
        
        users_dict = {}
        if mentions.includes and 'users' in mentions.includes:
            users_dict = {u.id: u for u in mentions.includes['users']}
        
        for mention in mentions.data:
            newest_id = max(newest_id, int(mention.id))
            
            if mention.author_id in users_dict:
                username = users_dict[mention.author_id].username
            else:
                try:
                    user = client.get_user(id=mention.author_id).data
                    username = user.username
                except Exception as e:
                    logging.error(f"Could not get username for author ID {mention.author_id}: {e}")
                    continue
                
            logging.info(f"Processing mention {mention.id} from @{username}")
            
            tweet_text = mention.text
            wallet_address, token_address = extract_wallet_and_token(tweet_text)
            vote_token_address, vote_side = extract_vote_request(tweet_text)
            
            reply_text = f"@{username} "
            
            if vote_token_address and vote_side is not None:
                logging.info(f"Detected vote request for token {vote_token_address}, side: {vote_side}")
                try:
                    vote_result = vote_token(vote_token_address, vote_side)
                    if vote_result["success"]:
                        vote_data = vote_result["data"]
                        reply_text += (f"Vote recorded for token {vote_token_address[:6]}...{vote_token_address[-4:]}!\n"
                                      f"Upvotes: {vote_data['up']}, Downvotes: {vote_data['down']}, "
                                      f"User voted: {'Yes' if vote_data['userVoted'] else 'No'}")
                        client.create_tweet(
                            text=reply_text,
                            in_reply_to_tweet_id=mention.id
                        )
                        logging.info(f"Successfully replied to vote request on tweet {mention.id}")
                    else:
                        reply_text += f"Failed to vote on token {vote_token_address[:6]}...: {vote_result['message']}"
                        client.create_tweet(
                            text=reply_text,
                            in_reply_to_tweet_id=mention.id
                        )
                        logging.warning(f"Vote failed for {vote_token_address}: {vote_result['message']}")
                except Exception as e:
                    logging.error(f"Unexpected error when voting on {vote_token_address}: {e}")
                    reply_text += "An error occurred while processing your vote request."
                    client.create_tweet(
                        text=reply_text,
                        in_reply_to_tweet_id=mention.id
                    )
                continue  # Skip other processing if vote was handled
            
            if wallet_address and token_address:
                logging.info(f"Found wallet address: {wallet_address} and token address: {token_address}")
                
                try:
                    graph_result = get_insider_graph(token_address)
                    if graph_result["success"]:
                        holdings_info = check_wallet_holdings(wallet_address, graph_result["data"])
                        if holdings_info["found"]:
                            reply_text += (f"Wallet {wallet_address[:6]}...{wallet_address[-4:]} holds {holdings_info['holdings']} tokens "
                                          f"({'participant' if holdings_info['participant'] else 'non-participant'}).\n\n")
                        else:
                            reply_text += f"Wallet {wallet_address[:6]}...{wallet_address[-4:]} not found in the insider graph for this token.\n\n"
                    else:
                        reply_text += f"Couldn't fetch insider graph: {graph_result['message']}.\n\n"
                    
                    report = get_tokenreport(token_address)
                    if report and "normalized_score" in report:
                        report_text = create_report_text(report, token_address)
                        reply_text += "Here's the token risk report:"
                        
                        try:
                            image_path = infoimage.create_report_image(report, token_address)
                            media = api.media_upload(image_path)
                            
                            client.create_tweet(
                                text=reply_text,
                                media_ids=[media.media_id_string],
                                in_reply_to_tweet_id=mention.id
                            )
                            logging.info(f"Successfully replied to tweet {mention.id}")
                        except Exception as e:
                            logging.error(f"Image creation or upload failed: {e}")
                            reply_text += f"\n\n{report_text[:240]}..."
                            client.create_tweet(
                                text=reply_text,
                                in_reply_to_tweet_id=mention.id
                            )
                    else:
                        reply_text += f"Sorry, I couldn't retrieve a valid risk report for {token_address[:6]}... (the token may be invalid or not supported)."
                        client.create_tweet(
                            text=reply_text,
                            in_reply_to_tweet_id=mention.id
                        )
                        logging.warning(f"Failed to get valid report for {token_address}")
                except Exception as e:
                    logging.error(f"Unexpected error when processing {token_address}: {e}")
                    reply_text += "An error occurred while processing your request."
                    client.create_tweet(
                        text=reply_text,
                        in_reply_to_tweet_id=mention.id
                    )
            else:
                try:
                    tweet_text_lower = tweet_text.lower()
                    relevant_keywords = ["token", "report", "risks", "check", "rugcheck", "scam"]
                    if any(keyword in tweet_text_lower for keyword in relevant_keywords):
                        token_address = extract_token_address(tweet_text)
                        if token_address:
                            report = get_tokenreport(token_address)
                            if report and "normalized_score" in report:
                                report_text = create_report_text(report, token_address)
                                reply_text += "Here's your token report:"
                                
                                try:
                                    image_path = infoimage.create_report_image(report, token_address)
                                    media = api.media_upload(image_path)
                                    
                                    client.create_tweet(
                                        text=reply_text,
                                        media_ids=[media.media_id_string],
                                        in_reply_to_tweet_id=mention.id
                                    )
                                    logging.info(f"Successfully replied to tweet {mention.id}")
                                except Exception as e:
                                    logging.error(f"Image creation or upload failed: {e}")
                                    reply_text += f"\n\n{report_text[:240]}..."
                                    client.create_tweet(
                                        text=reply_text,
                                        in_reply_to_tweet_id=mention.id
                                    )
                            else:
                                reply_text += f"Sorry, I couldn't retrieve a valid report for {token_address[:6]}... (the token may be invalid or not supported)."
                                client.create_tweet(
                                    text=reply_text,
                                    in_reply_to_tweet_id=mention.id
                                )
                                logging.warning(f"Failed to get valid report for {token_address}")
                        else:
                            reply_text += "I couldn't find a valid token address in your tweet. Please include a token address."
                            client.create_tweet(
                                text=reply_text,
                                in_reply_to_tweet_id=mention.id
                            )
                            logging.info(f"No token address found in mention {mention.id}")
                except Exception as e:
                    logging.error(f"Twitter API error: {e}")
        
        return newest_id
    except Exception as e:
        logging.error(f"Error retrieving mentions: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return last_id

def main():
    global client, api
    client = tweepy.Client(
        bearer_token=credentials.BEARER_TOKEN,
        consumer_key=credentials.API_KEY,
        consumer_secret=credentials.API_SECRET_KEY,
        access_token=credentials.ACCESS_TOKEN,
        access_token_secret=credentials.ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True
    )
    
    auth = tweepy.OAuth1UserHandler(
        credentials.API_KEY,
        credentials.API_SECRET_KEY,
        credentials.ACCESS_TOKEN,
        credentials.ACCESS_TOKEN_SECRET
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)
    
    try:
        me = client.get_me()
        logging.info(f"Authentication successful, connected as @{me.data.username}")
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return
    
    try:
        with open("last_id.txt", "r") as f:
            last_id = int(f.read().strip())
            logging.info(f"Starting with last ID: {last_id}")
    except FileNotFoundError:
        last_id = 1
        logging.info("No last ID found, starting from beginning")
    
    logging.info("Starting Twitter bot...")
    
    while True:
        try:
            new_last_id = respondToTweet(last_id)
            if new_last_id != last_id:
                last_id = new_last_id
                with open("last_id.txt", "w") as f:
                    f.write(str(last_id))
                logging.info(f"Updated last ID to: {last_id}")
            
            logging.info("Waiting for next check cycle...")
            time.sleep(900)
        except tweepy.RateLimitError as e:
            logging.warning("Rate limit exceeded, waiting longer...")
            time.sleep(900)
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            logging.info("Waiting 60 seconds before retry...")
            time.sleep(60)

if __name__ == "__main__":
    main()