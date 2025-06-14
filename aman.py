import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Global state dictionaries
user_predict_state = {}
user_dice_state = {} # Used for "Dice" game in Emojis Casino
single_emoji_bets = {}
user_referral_data = {} # Dictionary to store referral data

# New global state for the /dice command game
user_dice_match_state = {}

# State for tracking the game flow for the dice match, including message IDs for editing
user_game_flow_state = {}


def get_predict_keyboard(state, fast_mode=False, last_outcome=None):
    chosen = state.get('chosen', [])
    keyboard = [
        [
            InlineKeyboardButton(f"{'✅' if 1 in chosen else ''}1", callback_data="predict_num_1"),
            InlineKeyboardButton(f"{'✅' if 2 in chosen else ''}2", callback_data="predict_num_2"),
            InlineKeyboardButton(f"{'✅' if 3 in chosen else ''}3", callback_data="predict_num_3"),
            InlineKeyboardButton(f"{'✅' if 4 in chosen else ''}4", callback_data="predict_num_4"),
            InlineKeyboardButton(f"{'✅' if 5 in chosen else ''}5", callback_data="predict_num_5"),
            InlineKeyboardButton(f"{'✅' if 6 in chosen else ''}6", callback_data="predict_num_6"),
        ],
        [
            InlineKeyboardButton("1-3", callback_data="predict_range_1_3"),
            InlineKeyboardButton("4-6", callback_data="predict_range_4_6"),
        ],
        [
            InlineKeyboardButton("1-2", callback_data="predict_range_1_2"),
            InlineKeyboardButton("3-4", callback_data="predict_range_3_4"),
            InlineKeyboardButton("5-6", callback_data="predict_5-6"),
        ],
        [
            InlineKeyboardButton("ODD", callback_data="predict_odd"),
            InlineKeyboardButton("EVEN" + (" 🔄" if last_outcome == "EVEN" else "") if last_outcome is not None else "", callback_data="predict_even"),
        ],
        [
            InlineKeyboardButton("Bet amount", callback_data="predict_bet_amount")
        ],
        [
            InlineKeyboardButton(f"Minimum amount is ₹0", callback_data="predict_min_amount")
        ]
    ]
    if fast_mode:
        keyboard.append([
            InlineKeyboardButton("⬅️ BACK", callback_data="predict_fastbet_off")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("Roll 🎲", callback_data="predict_roll")
        ])
        keyboard.append([
            InlineKeyboardButton("⬅️ BACK", callback_data="back_to_emoji_games")
        ])
    return InlineKeyboardMarkup(keyboard)

def format_outcome(chosen):
    if chosen == [1,2,3,4,5,6]:
        return "ANY"
    if chosen == [2,4,6]:
        return "EVEN"
    if chosen == [1,3,5]:
        return "ODD"
    if chosen == [1,2,3]:
        return "1-3"
    if chosen == [4,5,6]:
        return "4-6"
    if chosen == [1,2]:
        return "1-2"
    if chosen == [3,4]:
        return "3-4"
    if chosen == [5,6]:
        return "5-6"
    if len(chosen) == 1:
        return str(chosen[0])
    return ",".join(map(str, chosen))

def get_predict_text(state, fast_mode=False):
    chosen = sorted(state.get('chosen', []))
    bet = state.get('bet', 0.0)
    balance = state.get('balance', 0.0)
    if 'last_outcome' in state and state['last_outcome']:
        outcome = ','.join(map(str, state['last_outcome']))
        multiplier = state.get('last_multiplier', 0.0)
        won = state.get('last_win', False)
        win_amount = round(bet * multiplier, 2) if won else 0
        bet_text = f"₹{bet} → ₹{win_amount}"
    else:
        outcome = "—"
        multiplier = round(6 / len(chosen), 2) if chosen else "—"
        bet_text = f"₹{bet} → ₹—"
    if fast_mode:
        return (
            "🔮 <b>Predict</b>\n\n"
            "You can also <b>send many dice yourself</b>\n"
            "and get your <b>bets summary</b> at the end!\n\n"
            f"Outcome: <b>{format_outcome(chosen)}</b>\n"
            f"Multiplier: <b>{multiplier}x</b>\n"
            f"Bet amount: {bet_text}\n"
            f"Balance: ₹{balance}\n\n"
            "<b>Fast-bet mode ON</b>\n"
            "Any outcome clicked will place a bet.\n"
            "Click back to turn it off."
        )
    else:
        return (
            "🔮 <b>Predict</b>\n\n"
            "<i>Choose dice outcome, bet amount and try your luck!</i>\n\n"
            "You can <b>send many dice yourself</b> and get your <b>bets summary</b> at the end!\n\n"
            f"Outcome: {outcome}\n"
            f"Multiplier: {multiplier if multiplier != 0 else '—'}x\n"
            f"Bet amount: {bet_text}\n"
            f"Balance: ₹{balance}\n"
        )

# --- Crypto Deposit Buttons ---
CRYPTO_BUTTONS = [
    ["Bitcoin (BTC)", "Litecoin (LTC)"],
    ["Dogecoin (DOGE)", "Ethereum (ETH)"],
    ["Tron (TRX)", "BNB (BNB)"],
    ["Ripple (XRP)", "Polygon (POL)"],
    ["Ethereum (BASE)", "Solana (SOL)"],
    ["Toncoin (TON)", "Monero (XMR)"],
    ["USDT (TON)", "USDT (TRC20)"],
    ["USDT (ERC20)", "USDC (ERC20)"],
    ["USDT (BEP20)", "USDC (BEP20)"],
    ["USDC (BASE)", "USDT (SOL)"],
    ["USDC (SOL)", "USDT (POL)"]
]

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "<b>Deposit</b> - no minimum amount\n\n"
        "Deposits are credited as soon as 1 blockchain confirmation is reached.\n"
    )
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton(text) for text in row] + ([KeyboardButton("⬅️ BACK")] if i == len(CRYPTO_BUTTONS) - 1 else []) for i, row in enumerate(CRYPTO_BUTTONS)],
        resize_keyboard=True
    )
    # Corrected: Check if update.message exists, otherwise use update.callback_query.message
    if update.message:
        await update.message.reply_text(
            msg,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            msg,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

def get_bet_summary_text(outcome_str, multiplier, bet):
    return (
        f"🔮 <b>Predict - Bet placed</b>\n\n"
        f"Outcome: <b>{outcome_str}</b>\n"
        f"Multiplier: <b>{multiplier}x</b>\n"
        f"Bet amount: ₹{bet} → ₹{bet if bet else 0}\n\n"
        "<i>Rolling...</i>"
    )

def get_dice_keyboard(state):
    game_types = [
        ("dice", "🎲"),
        ("bowling", "🎳"),
        ("dart", "🎯"),
        ("soccer", "⚽"),
        ("basket", "🏀"),
    ]
    selected_game = state.get("game", "dice")
    game_row = [
        InlineKeyboardButton(
            f"{emoji}{'✅' if selected_game == key else ''}",
            callback_data=f"dice_game_{key}"
        ) for key, emoji in game_types
    ]
    first_to = state.get("first_to", 3)
    first_to_row = [
        InlineKeyboardButton(
            f"{num}{'✅' if first_to == num else ''}",
            callback_data=f"dice_firstto_{num}"
        ) for num in range(1, 6)
    ]
    rolls = state.get("rolls", 1)
    rolls_row = [
        InlineKeyboardButton(
            f"{num}{'✅' if rolls == num else ''}",
            callback_data=f"dice_rolls_{num}"
        ) for num in range(1, 4)
    ]
    bet_row = [
        InlineKeyboardButton("₹0 - 100%", callback_data="dice_bet")
    ]
    play_btn = []
    if state.get("bet", 0) > 0:
        play_btn = [InlineKeyboardButton("Play 🎲", callback_data="dice_play")]
    return InlineKeyboardMarkup([
        game_row,
        first_to_row,
        rolls_row,
        bet_row,
        play_btn,
        [InlineKeyboardButton("Back", callback_data="back_to_emoji_games")]
    ])

def get_dice_text(state):
    balance = state.get("balance", 0.0)
    first_to = state.get("first_to", 3)
    rolls = state.get("rolls", 1)
    multiplier = 1.92
    win_chance = 50
    rounds_user = state.get("rounds_user", 0)
    rounds_bot = state.get("rounds_bot", 0)
    last_result = state.get("last_result", "")
    bet = state.get("bet", 0)
    game = state.get('game', 'dice')
    if game == "dart":
        title = "🎯 <b>Dart</b>"
        description = (
            "Match against the bot, 1 roll each, highest roll wins the round. First to reach 3 rounds wins the match.\n"
        )
    elif game == "bowling":
        title = "🎳 <b>Bowling</b>"
        description = (
            "Match against the bot, 1 roll each, highest roll wins the round. First to reach 3 rounds wins the match.\n"
        )
    elif game == "soccer":
        title = "⚽ <b>Soccer</b>"
        description = (
            "Match against the bot, 1 roll each, highest roll wins the round. First to reach 3 rounds wins the match.\n"
        )
    elif game == "basket":
        title = "🏀 <b>Basket</b>"
        description = (
            "Match against the bot, 1 roll each, highest roll wins the round. First to reach 3 rounds wins the match.\n"
        )
    else:
        title = "🎲 <b>Dice</b>"
        description = (
            "Match against the bot, 1 roll each, highest roll wins the round. First to reach 3 rounds wins the match.\n"
        )
    text = (
        f"{title}\n"
        f"{description}"
        f"Multiplier: <b>{multiplier}x</b>\n"
        f"Winning chance: {win_chance}%\n\n"
        f"Balance: ₹{balance}\n\n"
        f"<b>Game</b>: {state.get('game','dice').capitalize()}\n"
        f"<b>First to</b>: {first_to}\n"
        f"<b>Rolls count</b>: {rolls}\n"
        f"<b>Bet amount</b>: ₹{bet}\n"
    )
    if rounds_user or rounds_bot:
        text += f"\nYou: {rounds_user} | Bot: {rounds_bot}\n"
    if last_result:
        text += f"\n{last_result}\n"
    return text

def get_currency_keyboard(selected="INR"):
    currency_rows = [
        ["$", "€", "¥", "£"],
        ["CNY", "KRW", "INR", "CAD"],
        ["HKD", "BRL", "AUD", "TWD"],
        ["CHF", "RUB", "THB", "SAR"],
        ["AED", "PLN", "VND", "IDR"],
        ["SEK", "TRY", "PHP", "NOK"],
        ["CZK", "HUF", "UAH", "ARS"],
        ["BTC", "LTC", "TON", "ETH"],
        ["TRX", "SOL", "BNB", "XMR"],
        ["TRUMP", "XRP", "POL", "ARB"],
        ["AVAX", "SHIB", "PEPE", "DOGE"],
        ["KAS"]
    ]
    keyboard = []
    for row in currency_rows:
        row_buttons = []
        for code in row:
            display = f"{code}✅" if code == selected else code
            row_buttons.append(InlineKeyboardButton(display, callback_data=f"currency_{code}"))
        keyboard.append(row_buttons)
    keyboard.append([InlineKeyboardButton("⬅️ BACK", callback_data="settings_back")])
    return InlineKeyboardMarkup(keyboard)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal_predict = user_predict_state.get(user_id, {}).get("balance", 0.0)
    bal_dice = user_dice_state.get(user_id, {}).get("balance", 0.0)
    balance = max(bal_predict, bal_dice) # Assuming a shared balance for simplicity
    await update.message.reply_text(
        f"💰 Your account balance:\n\n<b>₹{balance:.2f}</b>",
        parse_mode="HTML"
    )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    privacy_state = context.user_data.get("privacy", True)
    privacy_text = "✅ Privacy" if privacy_state else "Privacy"
    settings_keyboard = [
        [
            InlineKeyboardButton("💱 Currency", callback_data="settings_currency"),
            InlineKeyboardButton(privacy_text, callback_data="settings_privacy")
        ],
        [
            InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")
        ]
    ]
    # Check if update.message exists (for command) or update.callback_query (for inline button)
    if update.message:
        await update.message.reply_text(
            "⚙️ <b>Settings</b>",
            reply_markup=InlineKeyboardMarkup(settings_keyboard),
            parse_mode="HTML"
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text( # Use edit_message_text for callback queries
            "⚙️ <b>Settings</b>",
            reply_markup=InlineKeyboardMarkup(settings_keyboard),
            parse_mode="HTML"
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Correctly extract user_id based on the Update type
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        username = update.callback_query.from_user.username
        message = update.callback_query.message
    else:
        user_id = update.effective_user.id
        username = update.effective_user.username
        message = update.message

    # Generate a unique referral code if one doesn't exist.
    if user_id not in user_referral_data:
        import base64
        referral_code = base64.urlsafe_b64encode(str(user_id).encode()).decode().rstrip('=')
        user_referral_data[user_id] = {
            "code": referral_code,
            "referred_users": [],
            "earnings": 0.0
        }
    else:
        referral_code = user_referral_data[user_id]["code"]

    # Construct the referral link. Replace 'YOUR_BOT_USERNAME' with your actual bot's username.
    # IMPORTANT: Replace 'YOUR_BOT_USERNAME' with your actual Telegram bot's username!
    referral_link = f"https://t.me/YOUR_BOT_USERNAME?start={referral_code}"
    
    referred_count = len(user_referral_data[user_id]["referred_users"])
    total_earnings = user_referral_data[user_id]["earnings"]

    referral_text = (
        "<b>💰 Refer and Earn!</b>\n\n"
        f"Share your unique referral link to bring new souls into our den of depravity!\n"
        f"For every new minion you recruit, and for their glorious contributions, you shall be rewarded.\n\n"
        f"Your Referral Link: <code>{referral_link}</code>\n"
        f"Referred Minions: <b>{referred_count}</b>\n"
        f"Total Blood Money Earned: <b>₹{total_earnings:.2f}</b>\n\n"
        "<i>The more you corrupt, the more you earn, Master!</i>"
    )

    keyboard = [[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text( # Use 'message' to reply, as update.message might be None for callback queries
        referral_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check for referral code if the user started with a deep link
    if context.args:
        referred_by_code = context.args[0]
        referrer_id = None
        for uid, data in user_referral_data.items():
            if data["code"] == referred_by_code:
                referrer_id = uid
                break
        
        if referrer_id and update.effective_user.id not in user_referral_data[referrer_id]["referred_users"]:
            user_referral_data[referrer_id]["referred_users"].append(update.effective_user.id)
            # Implement your desired referral bonus here. For example, giving the referrer 10 units of currency.
            user_referral_data[referrer_id]["earnings"] += 10.0 
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"A new minion, {update.effective_user.mention_html()}, has joined our ranks through your link! You've earned ₹10.00!",
                parse_mode="HTML"
            )

    keyboard = [
        [InlineKeyboardButton("🎁 Deposit gifts", callback_data="/depositgifts")],
        [InlineKeyboardButton("📈 Predictions", callback_data="/predictions"),
         InlineKeyboardButton("🚀 Crash", url="https://t.me/DenaroCasinoBot/crash")],
        [InlineKeyboardButton("👥 Join Group", callback_data="/joingroup")],
        [InlineKeyboardButton("🎱 Games", callback_data="/games")], # This is the button that sends '/games'
        [InlineKeyboardButton("📥 Deposit", callback_data="/deposit"),
         InlineKeyboardButton("📤 Withdraw", callback_data="/withdraw")],
        [InlineKeyboardButton("💰 Refer and Earn", callback_data="/refer")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="/settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to Denaro Casino!\nSelect an option:",
        reply_markup=reply_markup
    )

# SLOTS helper function
async def show_slots_game(query, context, slots_state):
    balance = slots_state.get("balance", 100.0)
    bet = slots_state.get("bet", 10)
    last_result = slots_state.get("last_result", "")
    last_spin = slots_state.get("last_spin", ["❔", "❔", "❔"])
    msg = (
        f"🎰 <b>Slots</b>\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
        f"Result: {' | '.join(last_spin)}\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Spin 🎰", callback_data="slots_spin")],
        [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
    ])
    await query.edit_message_text(msg, reply_markup=markup, parse_mode="HTML")

# Climber helper function
async def show_climber_game(query, context, climber_state):
    balance = climber_state.get("balance", 100.0)
    cashout = climber_state.get("cashout", 1.0)
    crashed = climber_state.get("crashed", False)
    bet = climber_state.get("bet", 10)
    if crashed:
        text = f"🆕🚀 <b>Climber</b>\n\n<b>CRASHED!</b>\nYou lost your bet of ₹{bet}.\n\nBalance: ₹{balance:.2f}"
        buttons = [[InlineKeyboardButton("Play Again", callback_data="game_climber")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]]
    else:
        text = f"🆕🚀 <b>Climber</b>\n\nMultiplier: <b>{cashout:.2f}x</b>\nBet: ₹{bet}\nPotential win: ₹{bet*cashout:.2f}\nBalance: ₹{balance:.2f}\n\nClimb for higher multiplier or cashout any time!"
        buttons = [
            [InlineKeyboardButton("Climb 🚀", callback_data="climber_climb"),
             InlineKeyboardButton(f"Cashout ₹{bet*cashout:.2f}", callback_data="climber_cashout")],
            [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
        ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# Limbo helper function
async def show_limbo_game(query, context, limbo_state):
    balance = limbo_state.get("balance", 100.0)
    target = limbo_state.get("target", 2.0)
    bet = limbo_state.get("bet", 10)
    last_result = limbo_state.get("last_result", "")
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("−", callback_data="limbo_target_down"), InlineKeyboardButton(f"🎯 Target: {target:.2f}x", callback_data="noop"), InlineKeyboardButton("+", callback_data="limbo_target_up")],
        [InlineKeyboardButton("Bet", callback_data="limbo_bet")],
        [InlineKeyboardButton("Play Limbo 🚀", callback_data="limbo_play")],
        [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
    ])
    msg = (
        f"⚡ <b>Limbo</b>\n\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
        f"Target Multiplier: <b>{target:.2f}x</b>\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    msg += "\nSet your target multiplier and press play!"
    await query.edit_message_text(msg, reply_markup=markup, parse_mode="HTML")

async def show_hilo_game(query, context, hilo_state):
    balance = hilo_state.get("balance", 100.0)
    bet = hilo_state.get("bet", 10)
    card = hilo_state.get("card", None)
    last_result = hilo_state.get("last_result", "")
    markup = []
    msg = (
        f"♠️ <b>Hilo</b>\n\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    if card is None:
        # Draw a card for the user
        card = random.randint(2, 14)  # 2-10, J=11 Q=12 K=13 A=14
        hilo_state["card"] = card
        hilo_state["last_result"] = ""
        msg += f"\nYour Card: <b>{hilo_card_emoji(card)}</b>\n\nWill the next card be Higher or Lower?"
        markup = [
            [InlineKeyboardButton("Higher 🔼", callback_data="hilo_higher"),
             InlineKeyboardButton("Lower 🔽", callback_data="hilo_lower")],
            [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
        ]
    else:
        msg += f"\nYour Card: <b>{hilo_card_emoji(card)}</b>\n\nWill the next card be Higher or Lower?"
        markup = [
            [InlineKeyboardButton("Higher 🔼", callback_data="hilo_higher"),
             InlineKeyboardButton("Lower 🔽", callback_data="hilo_lower")],
            [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
        ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(markup), parse_mode="HTML")

def hilo_card_emoji(card):
    # Returns the value + emoji for the card
    if card == 11:
        return "J 🃏"
    elif card == 12:
        return "Q 👸"
    elif card == 13:
        return "K 🤴"
    elif card == 14:
        return "A 🅰️"
    else:
        return f"{card} 🂡"

async def show_mines_game(query, context, mines_state):
    grid = mines_state.get("grid", [0]*9)
    revealed = mines_state.get("revealed", [False]*9)
    bet = mines_state.get("bet", 10)
    balance = mines_state.get("balance", 100.0)
    last_result = mines_state.get("last_result", "")
    markup = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i+j
            text = "💣" if (revealed[idx] and grid[idx]) else ("🟩" if revealed[idx] else "❔")
            row.append(InlineKeyboardButton(text, callback_data=f"mines_reveal_{idx}"))
        markup.append(row)
    markup.append([InlineKeyboardButton("Cashout", callback_data="mines_cashout")])
    markup.append([InlineKeyboardButton("⬅️ Back", callback_data="regular_games")])
    msg = (
        f"💣 <b>Mines</b>\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
        f"Reveal safe tiles, avoid mines! Cashout anytime.\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(markup), parse_mode="HTML")

# Blackjack Helper Functions
def draw_card():
    card = random.choice(['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'])
    return card

def hand_value(hand):
    value = 0
    aces = 0
    for card in hand:
        if card == 'A':
            value += 11
            aces += 1
        elif card in ['J', 'Q', 'K']:
            value += 10
        else:
            value += int(card)
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

async def show_blackjack_game(query, context, bj_state):
    player = bj_state.get("player", [])
    dealer = bj_state.get("dealer", [])
    bet = bj_state.get("bet", 10)
    balance = bj_state.get("balance", 100.0)
    last_result = bj_state.get("last_result", "")
    markup = []
    player_val = hand_value(player)
    dealer_val_display = hand_value(dealer[:1])  # show only first dealer card
    msg = (
        f"🃏 <b>Blackjack</b>\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
        f"Your Hand: {', '.join(player)} ({player_val})\n"
        f"Dealer: {dealer[0]}, ❓\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    if player_val < 21 and not last_result:
        markup = [
            [InlineKeyboardButton("Hit", callback_data="bj_hit"),
             InlineKeyboardButton("Stand", callback_data="bj_stand")],
            [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
        ]
    else:
        markup = [
            [InlineKeyboardButton("Play Again", callback_data="game_blackjack")],
            [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
        ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(markup), parse_mode="HTML")

# Wheel Game Helper Function
async def show_wheel_game(query, context, wheel_state):
    balance = wheel_state.get("balance", 100.0)
    bet = wheel_state.get("bet", 10)
    last_result = wheel_state.get("last_result", "")
    msg = (
        f"🎯 <b>Wheel</b>\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Spin Wheel 🎯", callback_data="wheel_spin")],
        [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
    ])
    await query.edit_message_text(msg, reply_markup=markup, parse_mode="HTML")

# Roulette Helper Function
async def show_roulette_game(query, context, roulette_state):
    balance = roulette_state.get("balance", 100.0)
    bet = roulette_state.get("bet", 10)
    last_result = roulette_state.get("last_result", "")
    color_bet = roulette_state.get("color_bet", None)
    num_bet = roulette_state.get("num_bet", None)
    msg = (
        f"🎲 <b>Roulette</b>\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Bet: ₹{bet}\n"
    )
    if last_result:
        msg += f"\n{last_result}\n"
    markup = [
        [InlineKeyboardButton("Red 🔴", callback_data="roulette_bet_red"),
         InlineKeyboardButton("Black ⚫️", callback_data="roulette_bet_black"),
         InlineKeyboardButton("Green 🟩", callback_data="roulette_bet_green")],
        [InlineKeyboardButton("Number (pick 0-36)", callback_data="roulette_bet_number")],
        [InlineKeyboardButton("Spin 🎲", callback_data="roulette_spin")],
        [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
    ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(markup), parse_mode="HTML")

# Handler for /dice command (newly added)
async def start_dice_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    bet_amount = 10
    if args and args[0].isdigit():
        bet_amount = int(args[0])
    balance = user_dice_state.get(user_id, {}).get("balance", 100)
    if bet_amount > balance:
        await update.message.reply_text("Insufficient balance.")
        return
    user_dice_state.setdefault(user_id, {})["balance"] = balance - bet_amount
    user_dice_match_state[user_id] = {
        "user_rounds_won": 0,
        "bot_rounds_won": 0,
        "bet_amount": bet_amount,
        "balance": balance - bet_amount,
        "game_over": False
    }
    buttons = [
        [InlineKeyboardButton("Roll First Round 🎲", callback_data="dice_match_roll_round")],
        [InlineKeyboardButton("Cashout (forfeit)", callback_data="dice_match_cashout")]
    ]
    message = await update.message.reply_text(  # Store the message object
        f"🎲 <b>Dice Match Started!</b>\nFirst to 2 wins.\nBet: ₹{bet_amount}\nBalance: ₹{balance-bet_amount}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )
    user_game_flow_state[user_id] = {"dice_match_message_id": message.message_id}  # Store message ID

async def handle_dice_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or update.effective_user.username or "Player"

    if user_id not in user_game_flow_state or user_game_flow_state[user_id]['state'] != 'AWAITING_USER_DICE_ROLL':
        return

    if not update.message.dice or update.message.dice.emoji != '🎲':
        await update.message.reply_text("Please send a 🎲 emoji to roll your dice.")
        return

    user_score = update.message.dice.value

    game_flow_state = user_game_flow_state[user_id]
    chat_id = game_flow_state['game_message_chat_id']

    # Remove temp prompt message agar hai
    if game_flow_state.get('temp_prompt_message_id'):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=game_flow_state['temp_prompt_message_id'])
        except Exception:
            pass
        game_flow_state['temp_prompt_message_id'] = None

    # Bot ka dice roll (animated)
    bot_dice_msg = await context.bot.send_dice(chat_id=chat_id, emoji='🎲')
    await asyncio.sleep(2)
    bot_score = bot_dice_msg.dice.value

    # State update
    dice_match_state = user_dice_match_state.setdefault(user_id, {})
    bet_amount = dice_match_state.get("bet_amount", 0)
    current_balance = dice_match_state.get("balance", 100.0)

    dice_match_state["last_user_roll"] = user_score
    dice_match_state["last_bot_roll"] = bot_score

    if user_score > bot_score:
        dice_match_state["user_rounds_won"] += 1
    elif bot_score > user_score:
        dice_match_state["bot_rounds_won"] += 1
    # else draw: koi round nahi badhega

    user_rounds = dice_match_state["user_rounds_won"]
    bot_rounds = dice_match_state["bot_rounds_won"]

    # 1. Score bubble bhejo
    score_msg = f"<b>{username}</b> – {user_rounds}\nBot – {bot_rounds}"
    await context.bot.send_message(chat_id=chat_id, text=score_msg, parse_mode="HTML")

    # 2. Cashout ya result bubble bhejo
    game_over = False
    win_amount = 0
    multiplier = 0.33  # Default for ongoing round

    if user_rounds >= 2:
        game_over = True
        win_amount = int(bet_amount * 2)
        multiplier = 2.0
        dice_match_state["balance"] = current_balance + win_amount
        await context.bot.send_message(chat_id=chat_id, text=f"Cashout {multiplier:.2f}x (₹{win_amount})")
        await context.bot.send_message(chat_id=chat_id, text=f"🎉 <b>YOU WON THE MATCH!</b> You win ₹{win_amount}.", parse_mode="HTML")
    elif bot_rounds >= 2:
        game_over = True
        multiplier = 0.0
        win_amount = 0
        dice_match_state["balance"] = current_balance
        await context.bot.send_message(chat_id=chat_id, text=f"Cashout {multiplier:.2f}x (₹0)")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ <b>BOT WON THE MATCH!</b> You lost ₹{bet_amount}.", parse_mode="HTML")
    else:
        # Mid-game cashout bubble (always 0.33x, ₹0 for demo)
        await context.bot.send_message(chat_id=chat_id, text=f"Cashout 0.33x (₹0)")

    if game_over:
        # Clean up states
        user_dice_state.setdefault(user_id, {})["balance"] = dice_match_state["balance"]
        if user_id in user_game_flow_state:
            del user_game_flow_state[user_id]
        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
    else:
        user_game_flow_state[user_id]['state'] = 'GAME_IN_PROGRESS'

    # Delete user's dice message to keep chat clean
    try:
        await update.message.delete()
    except Exception:
        pass


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or query.from_user.username or "Player"
    await query.answer()

    # Dice Match: Handle dice match round roll
    if query.data == "dice_match_roll_round":
        match_state = user_dice_match_state.get(user_id)
        if not match_state or match_state.get("game_over"):
            await query.answer("No active match or match already finished.", show_alert=True)
            return

        # User and bot both roll dice
        user_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        match_state["last_user_roll"] = user_roll
        match_state["last_bot_roll"] = bot_roll

        # Decide round winner
        if user_roll > bot_roll:
            match_state["user_rounds_won"] += 1
            round_result = f"🎉 <b>You win this round!</b>"
        elif bot_roll > user_roll:
            match_state["bot_rounds_won"] += 1
            round_result = f"🤖 <b>Bot wins this round!</b>"
        else:
            round_result = f"🤝 <b>Draw!</b> No one gets this round."

        # Check if anyone won the match (first to 2)
        if match_state["user_rounds_won"] >= 2 or match_state["bot_rounds_won"] >= 2:
            match_state["game_over"] = True
            if match_state["user_rounds_won"] > match_state["bot_rounds_won"]:
                match_state["final_result_message"] = f"🏆 <b>You win the match!</b>\nYou won ₹{match_state['bet_amount']}!"
                # Add winnings to balance
                match_state["balance"] += match_state["bet_amount"]*2
                user_dice_state.setdefault(user_id, {})["balance"] = match_state["balance"]
            else:
                match_state["final_result_message"] = f"😢 <b>Bot wins the match!</b>\nYou lost ₹{match_state['bet_amount']}."
            match_summary = (
                f"🎲 <b>Dice Match Update</b>\n"
                f"Your Roll: <b>{user_roll}</b>\n"
                f"Bot Roll: <b>{bot_roll}</b>\n"
                f"{round_result}\n\n"
                f"Score: You {match_state['user_rounds_won']} - {match_state['bot_rounds_won']} Bot\n\n"
                f"{match_state['final_result_message']}\n"
                f"Current Balance: ₹{match_state['balance']:.2f}"
            )
            # End of game, offer to play again
            buttons = [
                [InlineKeyboardButton("Play Again", callback_data="/dice")],
                [InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")]
            ]
            await context.bot.edit_message_text(  # Use bot.edit_message_text
                chat_id=query.message.chat_id,
                message_id=user_game_flow_state[user_id]["dice_match_message_id"],  # Get message ID
                text=match_summary,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML"
            )
        else:
            # Game still running, send update and option to roll next round
            match_summary = (
                f"🎲 <b>Dice Match Update</b>\n"
                f"Your Roll: <b>{user_roll}</b>\n"
                f"Bot Roll: <b>{bot_roll}</b>\n"
                f"{round_result}\n\n"
                f"Score: You {match_state['user_rounds_won']} - {match_state['bot_rounds_won']} Bot\n"
                f"First to 2 wins.\n"
                f"Current Balance: ₹{match_state['balance']:.2f}\n\n"
                f"Ready for next round?"
            )
            buttons = [
                [InlineKeyboardButton("Roll Next Round 🎲", callback_data="dice_match_roll_round")],
                [InlineKeyboardButton("Cashout (forfeit)", callback_data="dice_match_cashout")]
            ]
            await context.bot.edit_message_text(  # Use bot.edit_message_text
                chat_id=query.message.chat_id,
                message_id=user_game_flow_state[user_id]["dice_match_message_id"],  # Get message ID
                text=match_summary,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML"
            )
        return
    # Handle /refer button
    if query.data == "/refer":
        await refer(update, context)
        return

    # Handle /deposit button from inline keyboard
    if query.data == "/deposit":
        await deposit(update, context)
        return

    # Handle /settings button
    if query.data == "/settings":
        await settings(update, context)
        return

    # Handle /games button to show the main games menu
    if query.data == "/games":
        games_keyboard = [
            [
                InlineKeyboardButton("🎲 Emojis Casino", callback_data="emoji_casino"),
                InlineKeyboardButton("💣 Regular Games", callback_data="regular_games"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")
            ]
        ]
        games_text = (
            "<b>Games</b>\n\n"
            "Choose between emojis-based games and regular ones, all provably fair!"
        )
        await query.edit_message_text(
            games_text,
            reply_markup=InlineKeyboardMarkup(games_keyboard),
            parse_mode="HTML"
        )
        return

    # Handle specific crypto button presses (if it was a ReplyKeyboardMarkup, this would be triggered by message text)
    # However, for consistency and future expansion with InlineKeyboards, we handle it here.
    # Note: When using ReplyKeyboardMarkup, the user's *message text* becomes the query.text/message.text, not query.data.
    # This part handles the case where the user *taps* a reply keyboard button, and then it's processed as a message.
    # So, we check query.message.text (which is populated when a ReplyKeyboardButton is tapped).
    if query.message and query.message.text == "USDT (BEP20)": # Ensure query.message exists
        address = "0xb7264924c0b20a0d9f1b0c5ea0e65c4d276d99cc"
        deposit_text = f"USDT (BEP20) Deposit Address:\n`{address}`\n\nSend USDT (BEP20) to the address above. Deposits are credited as soon as 1 blockchain confirmation is reached."
        deposit_keyboard = [
            [
                InlineKeyboardButton("Confirm ✅", callback_data="deposit_confirm"),
                InlineKeyboardButton("Refresh 🔄", callback_data="deposit_refresh")
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_deposit_crypto_selection")
            ]
        ]
        await query.message.reply_text(
            deposit_text,
            reply_markup=InlineKeyboardMarkup(deposit_keyboard),
            parse_mode="Markdown" # Use Markdown for code block formatting
        )
        return

    # Handlers for Confirm and Refresh deposit buttons
    if query.data == "deposit_confirm":
        await query.message.reply_text("Your deposit confirmation has been noted. Awaiting blockchain verification.")
        return
    if query.data == "deposit_refresh":
        await query.message.reply_text("Refreshing deposit status. Please wait for the blockchain to update.")
        return
    if query.data == "back_to_deposit_crypto_selection":
        await deposit(update, context) # Go back to the main deposit selection
        return


    # --- Regular Games Menu ---
    if query.data == "regular_games":
        regular_games_keyboard = [
            [
                InlineKeyboardButton("🆕🚀 Climber", callback_data="game_climber")
            ],
            [
                InlineKeyboardButton("⚡ Limbo", callback_data="game_limbo")
            ],
            [
                InlineKeyboardButton("♠️ Hilo", callback_data="game_hilo"),
                InlineKeyboardButton("💣 Mines", callback_data="game_mines")
            ],
            [
                InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
                InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack")
            ],
            [
                InlineKeyboardButton("🎯 Wheel", callback_data="game_wheel"),
                InlineKeyboardButton("🎲 Roulette", callback_data="game_roulette")
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")
            ]
        ]
        regular_games_text = (
            "<b>Regular Games</b>\n\n"
            "Not only emojis! Enjoy well-known casino games directly in your telegram app!"
        )
        await query.edit_message_text(
            regular_games_text,
            reply_markup=InlineKeyboardMarkup(regular_games_keyboard),
            parse_mode="HTML"
        )
        return

    # ----------------- SLOTS GAME (WORKING) -----------------
    if query.data == "game_slots":
        slots_state = context.user_data.setdefault("slots", {})
        slots_state["bet"] = 10
        slots_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        slots_state["last_result"] = ""
        slots_state["last_spin"] = ["❔", "❔", "❔"]
        await show_slots_game(query, context, slots_state)
        return

    if query.data == "slots_spin":
        slots_state = context.user_data.setdefault("slots", {})
        bet = slots_state.get("bet", 10)
        balance = slots_state.get("balance", 100.0)
        symbols = ["🍒", "🍋", "🍉", "⭐️", "💎", "7️⃣"]
        spin = [random.choice(symbols) for _ in range(3)]

        if balance < bet:
            slots_state["last_result"] = "Insufficient balance!"
            slots_state["last_spin"] = spin
        else:
            if spin[0] == spin[1] == spin[2]:
                win = bet * 10
                slots_state["last_result"] = f"🎉 JACKPOT! You win ₹{win}!"
                balance += win - bet
            elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
                win = bet * 2
                slots_state["last_result"] = f"Nice! You win ₹{win}!"
                balance += win - bet
            else:
                slots_state["last_result"] = f"No win. Try again!"
                balance -= bet
            slots_state["last_spin"] = spin
        slots_state["balance"] = balance
        if user_id not in user_dice_state:
            user_dice_state[user_id] = {}
        user_dice_state[user_id]["balance"] = balance
        await show_slots_game(query, context, slots_state)
        return

    # ----------------- END SLOTS GAME -----------------

    # --- Climber Game Logic ---
    if query.data == "game_climber":
        # Initialize Climber game state
        climber_state = context.user_data.setdefault("climber", {})
        climber_state["bet"] = 10
        climber_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        climber_state["cashout"] = 1.0
        climber_state["crashed"] = False
        climber_state["first_climb"] = True # Added flag for initial bet deduction
        await show_climber_game(query, context, climber_state)
        return

    if query.data == "climber_climb":
        climber_state = context.user_data.setdefault("climber", {})
        if climber_state.get("crashed"):
            await show_climber_game(query, context, climber_state)
            return

        bet = climber_state.get("bet", 10)
        current_balance = climber_state.get("balance", 100.0)

        # Deduct bet only on the very first climb of a new game round
        if climber_state.get("first_climb", True):
            if current_balance < bet:
                await query.answer("Not enough balance for the initial bet!", show_alert=True)
                return
            current_balance -= bet
            climber_state["balance"] = current_balance
            climber_state["first_climb"] = False # Mark that the initial bet has been deducted
            # Update global dice balance too
            user_dice_state.setdefault(user_id, {})["balance"] = current_balance

        cashout = climber_state.get("cashout", 1.0)
        # Each climb increases multiplier, but chance to crash increases
        cashout = round(cashout * random.uniform(1.1, 2.0), 2)
        crash_chance = min(0.15 + (cashout-1.0)*0.13, 0.8) # crash risk increases
        crashed = random.random() < crash_chance
        
        climber_state["cashout"] = cashout
        climber_state["crashed"] = crashed
        
        await show_climber_game(query, context, climber_state)
        return

    if query.data == "climber_cashout":
        climber_state = context.user_data.setdefault("climber", {})
        bet = climber_state.get("bet", 10)
        cashout = climber_state.get("cashout", 1.0)
        balance = climber_state.get("balance", 100.0) # This balance already has the initial bet deducted

        # If user cashed out immediately without clicking "Climb" (i.e., first_climb is still True)
        if climber_state.get("first_climb", True):
            # This scenario means they tried to cashout before any actual game play.
            # Refund the initial bet if it was deducted. Or, if no bet was deducted, no win/loss.
            climber_state["last_result"] = "Game not started. No win/loss."
            climber_state["crashed"] = True # End the game
            win = 0
        else:
            win = round(bet * cashout, 2)
            balance = balance + win # Add win to the balance (which already had the bet deducted)
            climber_state["last_result"] = f"<b>CASHED OUT</b> at <b>{cashout:.2f}x</b>! You win <b>₹{win:.2f}</b>!"
            climber_state["crashed"] = True # End the game

        climber_state["balance"] = balance
        # Update global dice balance too
        user_dice_state.setdefault(user_id, {})["balance"] = balance

        await query.edit_message_text(
            f"🆕🚀 <b>Climber</b>\n\n{climber_state['last_result']}\n\nBalance: ₹{balance:.2f}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Play Again", callback_data="game_climber")],
                [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
            ]),
            parse_mode="HTML"
        )
        return

    # --- LIMBO GAME LOGIC ---
    if query.data == "game_limbo":
        limbo_state = context.user_data.setdefault("limbo", {})
        limbo_state["target"] = 2.0
        limbo_state["bet"] = 10
        limbo_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        limbo_state["last_result"] = ""
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_target_up":
        limbo_state = context.user_data.setdefault("limbo", {})
        limbo_state["target"] = min(round(limbo_state.get("target", 2.0) + 0.1, 2), 10.0)
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_target_down":
        limbo_state = context.user_data.setdefault("limbo", {})
        limbo_state["target"] = max(round(limbo_state.get("target", 2.0) - 0.1, 2), 1.01)
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_bet":
        limbo_state = context.user_data.setdefault("limbo", {})
        bet = limbo_state.get("bet", 10)
        # Simple bet cycling (10 -> 50 -> 100 -> 10)
        limbo_state["bet"] = {10: 50, 50: 100, 100: 10}.get(bet, 10)
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_play":
        limbo_state = context.user_data.setdefault("limbo", {})
        bet = limbo_state.get("bet", 10)
        balance = limbo_state.get("balance", 100.0)
        target = limbo_state.get("target", 2.0)
        if bet > balance:
            limbo_state["last_result"] = "<b>Insufficient balance!</b>"
            await show_limbo_game(query, context, limbo_state)
            return

        payout = random.uniform(1.0, 10.0)
        if payout >= target:
            win = round(bet * target, 2)
            limbo_state["last_result"] = f"🎉 <b>WIN!</b> Multiplier: <b>{payout:.2f}x</b>\nYou won ₹{win}!"
            limbo_state["balance"] = round(balance - bet + win, 2)
        else:
            limbo_state["last_result"] = f"❌ <b>LOST!</b> Multiplier: <b>{payout:.2f}x</b>\nYou lost ₹{bet}!"
            limbo_state["balance"] = round(balance - bet, 2)

        # Also update global dice balance for consistency
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = limbo_state["balance"]

        await show_limbo_game(query, context, limbo_state)
        return

    # --- HILO GAME LOGIC ---
    if query.data == "game_hilo":
        hilo_state = context.user_data.setdefault("hilo", {})
        hilo_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        hilo_state["bet"] = 10
        hilo_state["card"] = None
        hilo_state["last_result"] = ""
        await show_hilo_game(query, context, hilo_state)
        return

    if query.data == "hilo_higher" or query.data == "hilo_lower":
        hilo_state = context.user_data.setdefault("hilo", {})
        bet = hilo_state.get("bet", 10)
        balance = hilo_state.get("balance", 100.0)
        card = hilo_state.get("card", None)
        if card is None:
            await show_hilo_game(query, context, hilo_state)
            return
        # Draw a new card
        next_card = random.randint(2, 14)
        if query.data == "hilo_higher":
            win = next_card > card
        else:
            win = next_card < card
        if card == next_card:
            # Draw, refund
            hilo_state["last_result"] = f"Draw! Next card was {hilo_card_emoji(next_card)}. Your bet is refunded."
            hilo_state["balance"] = balance
        elif win:
            win_amt = bet * 1.95
            hilo_state["last_result"] = f"🎉 WIN! Next card was {hilo_card_emoji(next_card)}. You won ₹{win_amt:.2f}!"
            hilo_state["balance"] = balance + win_amt
        else:
            hilo_state["last_result"] = f"❌ LOST! Next card was {hilo_card_emoji(next_card)}. You lost ₹{bet}."
            hilo_state["balance"] = balance - bet
        hilo_state["bet"] = 10
        hilo_state["card"] = None
        # Also update the global dice balance for consistency
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = hilo_state["balance"]
        await show_hilo_game(query, context, hilo_state)
        return

    # --- MINES GAME LOGIC ---
    if query.data == "game_mines":
        mines_state = context.user_data.setdefault("mines", {})
        mines_state["bet"] = 10
        mines_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        # Randomly place 3 mines
        grid = [0]*9
        for i in random.sample(range(9), 3):
            grid[i] = 1
        mines_state["grid"] = grid
        mines_state["revealed"] = [False]*9
        mines_state["last_result"] = ""
        mines_state["safe_revealed"] = 0
        mines_state["game_started"] = False # Reset game_started flag
        await show_mines_game(query, context, mines_state)
        return

    if query.data.startswith("mines_reveal_"):
        idx = int(query.data.split("_")[-1])
        mines_state = context.user_data.setdefault("mines", {})
        bet = mines_state.get("bet", 10)
        balance = mines_state.get("balance", 100.0)
        grid = mines_state.get("grid", [0]*9)
        revealed = mines_state.get("revealed", [False]*9)
        
        if revealed[idx]: # If already revealed, do nothing but refresh
            await query.answer("Tile already revealed!", show_alert=True)
            await show_mines_game(query, context, mines_state)
            return

        # Deduct bet on first reveal for Mines game.
        if mines_state.get("game_started", False) == False:
            if balance < bet:
                mines_state["last_result"] = "<b>Insufficient balance for this bet!</b>"
                await show_mines_game(query, context, mines_state)
                return
            balance -= bet
            mines_state["balance"] = balance
            mines_state["game_started"] = True # Mark game as started

        revealed[idx] = True
        if grid[idx]:  # Hit a mine
            mines_state["last_result"] = "Boom! You hit a mine. Lost bet."
            mines_state["revealed"] = [True if g else revealed[i] for i, g in enumerate(grid)] # Reveal all mines on game over
            mines_state["safe_revealed"] = 0 # Reset for next game
            mines_state["game_started"] = False # Reset game state for next round
        else: # Safe tile
            mines_state["safe_revealed"] = mines_state.get("safe_revealed", 0) + 1
            mines_state["last_result"] = f"Safe! {mines_state['safe_revealed']} revealed."
            mines_state["revealed"] = revealed
        
        # Update global dice balance for consistency
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        
        await show_mines_game(query, context, mines_state)
        return

    if query.data == "mines_cashout":
        mines_state = context.user_data.setdefault("mines", {})
        safe = mines_state.get("safe_revealed", 0)
        bet = mines_state.get("bet", 10)
        balance = mines_state.get("balance", 100.0)

        # If game was not started (no tiles revealed yet) and user tries to cashout
        if mines_state.get("game_started", False) == False:
            mines_state["last_result"] = "Game not started. No win/loss."
            # No change to balance if bet wasn't deducted
            final_balance = balance
        else: # Game was started and tiles were revealed
            profit = (bet * safe * 0.5) # This is the profit from safe tiles
            final_balance = balance + profit # Add profit to current balance (which already had initial bet deducted)
            mines_state["last_result"] = f"Cashed out! You win ₹{profit:.2f} profit." # Profit is the amount above the bet

        mines_state["balance"] = final_balance
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = final_balance
        
        # Reset game state for next round
        mines_state["safe_revealed"] = 0 
        mines_state["revealed"] = [False]*9 
        mines_state["game_started"] = False
        # Randomly place new mines for the next game display
        grid = [0]*9
        for i in random.sample(range(9), 3):
            grid[i] = 1
        mines_state["grid"] = grid

        await show_mines_game(query, context, mines_state)
        return
    
    # ----------------- BLACKJACK GAME (NEW) -----------------
    if query.data == "game_blackjack":
        bj_state = context.user_data.setdefault("bj", {})
        bj_state["bet"] = 10
        bj_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        
        # Deduct bet at the start of the Blackjack game
        if bj_state["balance"] < bj_state["bet"]:
            await query.answer("Insufficient balance to start Blackjack!", show_alert=True)
            return
        bj_state["balance"] -= bj_state["bet"]
        user_dice_state.setdefault(user_id, {})["balance"] = bj_state["balance"] # Update global balance

        bj_state["player"] = [draw_card(), draw_card()]
        bj_state["dealer"] = [draw_card(), draw_card()]
        bj_state["last_result"] = ""
        await show_blackjack_game(query, context, bj_state)
        return

    if query.data == "bj_hit":
        bj_state = context.user_data.setdefault("bj", {})
        if hand_value(bj_state["player"]) >= 21: # Prevent hitting if already 21 or busted
            await query.answer("Cannot hit!", show_alert=True)
            await show_blackjack_game(query, context, bj_state)
            return
        
        bj_state["player"].append(draw_card())
        
        # Check if busted immediately after hitting
        if hand_value(bj_state["player"]) > 21:
            bj_state["last_result"] = f"❌ Busted! You lose ₹{bj_state['bet']}."
            # Balance already deducted at start, no further change for loss.
            # No need to add back bet, it's a loss.
            # Reset state for next game, but don't reset balance
        
        await show_blackjack_game(query, context, bj_state)
        return

    if query.data == "bj_stand":
        bj_state = context.user_data.setdefault("bj", {})
        player_val = hand_value(bj_state["player"])
        dealer = bj_state["dealer"]
        bet = bj_state.get("bet", 10)
        balance = bj_state.get("balance", 100.0) # This balance already has the initial bet deducted
        
        # Dealer draws cards until 17 or more
        while hand_value(dealer) < 17:
            dealer.append(draw_card())
            
        dealer_val = hand_value(dealer)

        # Determine game result and update balance
        win_amount = 0
        if player_val > 21:
            bj_state["last_result"] = f"❌ Busted! You lose ₹{bet}."
            # Balance already deducted, nothing to add/subtract.
        elif dealer_val > 21:
            win_amount = bet * 2
            bj_state["last_result"] = f"🎉 Dealer busted! Dealer hand: {', '.join(dealer)} ({dealer_val}). You win ₹{win_amount}."
            balance += win_amount
        elif player_val > dealer_val:
            win_amount = bet * 2
            bj_state["last_result"] = f"🎉 You win! Dealer hand: {', '.join(dealer)} ({dealer_val}). Win ₹{win_amount}."
            balance += win_amount
        elif player_val == dealer_val:
            win_amount = bet # Refund the bet
            bj_state["last_result"] = f"Draw! Dealer hand: {', '.join(dealer)} ({dealer_val}). Bet refunded."
            balance += win_amount # Add back the refunded bet
        else:
            bj_state["last_result"] = f"❌ Dealer wins with {', '.join(dealer)} ({dealer_val})! You lose ₹{bet}."
            # Balance already deducted, nothing to add/subtract.
            
        bj_state["balance"] = balance
        # Update global user balance
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        await show_blackjack_game(query, context, bj_state)
        return
    # ----------------- END BLACKJACK GAME -----------------

    # ----------------- WHEEL GAME (NEW) -----------------
    if query.data == "game_wheel":
        wheel_state = context.user_data.setdefault("wheel", {})
        wheel_state["bet"] = 10
        wheel_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        wheel_state["last_result"] = ""
        await show_wheel_game(query, context, wheel_state)
        return

    if query.data == "wheel_spin":
        wheel_state = context.user_data.setdefault("wheel", {})
        bet = wheel_state.get("bet", 10)
        balance = wheel_state.get("balance", 100.0)
        segments = [2, 3, 5, 10, 20, 50, 0, 0, 0] # Values to win, 0 for loss
        
        if balance < bet:
            wheel_state["last_result"] = "Insufficient balance!"
        else:
            # Deduct bet before spin
            balance -= bet
            result = random.choice(segments)
            if result == 0:
                wheel_state["last_result"] = f"No win. Try again!"
            else:
                win = bet * result
                wheel_state["last_result"] = f"🎉 You win {result}x! Payout: ₹{win}."
                balance += win # Add win to balance after deducting bet
        
        wheel_state["balance"] = balance
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        await show_wheel_game(query, context, wheel_state)
        return
    # ----------------- END WHEEL GAME -----------------

    # ----------------- ROULETTE GAME (NEW) -----------------
    if query.data == "game_roulette":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["bet"] = 10
        roulette_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        roulette_state["last_result"] = ""
        roulette_state["color_bet"] = None
        roulette_state["num_bet"] = None
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_red":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["color_bet"] = "red"
        roulette_state["num_bet"] = None
        roulette_state["last_result"] = "Bet placed on RED."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_black":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["color_bet"] = "black"
        roulette_state["num_bet"] = None
        roulette_state["last_result"] = "Bet placed on BLACK."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_green":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["color_bet"] = "green"
        roulette_state["num_bet"] = None
        roulette_state["last_result"] = "Bet placed on GREEN (0)."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_number":
        roulette_state = context.user_data.setdefault("roulette", {})
        # For simplicity, always bet on 7 (you can ask user for input)
        roulette_state["num_bet"] = 7
        roulette_state["color_bet"] = None
        roulette_state["last_result"] = "Bet placed on NUMBER 7."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_spin":
        roulette_state = context.user_data.setdefault("roulette", {})
        bet = roulette_state.get("bet", 10)
        balance = roulette_state.get("balance", 100.0)
        color_bet = roulette_state.get("color_bet", None)
        num_bet = roulette_state.get("num_bet", None)
        
        if not (color_bet or num_bet):
            roulette_state["last_result"] = "Please place a bet (color or number) before spinning!"
            await show_roulette_game(query, context, roulette_state)
            return

        if balance < bet:
            roulette_state["last_result"] = "Insufficient balance!"
            await show_roulette_game(query, context, roulette_state)
            return

        # Deduct bet before spin
        balance -= bet

        result = random.randint(0, 36)
        if result == 0:
            result_color = "green"
        elif result % 2 == 0: # European roulette, 1-10, 19-28 red (odd), black (even). 11-18, 29-36 black (odd), red (even)
            # For simplicity, let's just assume even numbers are black, odd are red (except 0 green)
            result_color = "black"
        else:
            result_color = "red"
        
        msg = f"Result: <b>{result} ({result_color.title()})</b>\n"
        
        win_amount = 0
        if color_bet and color_bet == result_color:
            win_amount = bet * (14 if result_color == "green" else 2)
            msg += f"🎉 You win ₹{win_amount}!"
            balance += win_amount
        elif num_bet is not None and result == num_bet:
            win_amount = bet * 36
            msg += f"🎉 You win ₹{win_amount}!"
            balance += win_amount
        else:
            msg += "Lost the bet."
        
        roulette_state["balance"] = balance
        roulette_state["last_result"] = msg
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        await show_roulette_game(query, context, roulette_state)
        return
    # ----------------- END ROULETTE GAME -----------------

    # ----------------- DICE MATCH GAME (UPDATED FLOW) -----------------
    if query.data == "dice_match_prompt_roll": # Triggered by "Roll First/Next Round" button
        print(f"Entering dice_match_prompt_roll for user {user_id}")
        dice_match_state = user_dice_match_state.setdefault(user_id, {})
        if dice_match_state.get("game_over", False):
            await query.answer("Game is over. Start a new one with /dice.", show_alert=True)
            # Revert buttons to new game
            if user_id in user_game_flow_state:
                game_flow_state = user_game_flow_state[user_id]
                msg = (
                    f"🎲 <b>Dice Match Ended!</b>\n\n"
                    f"{dice_match_state.get('final_result_message', 'Game has ended.')}\n"
                    f"Final Balance: ₹{dice_match_state.get('balance', 100.0):.2f}\n"
                )
                buttons = [[InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")],
                           [InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")]]
                try:
                    await context.bot.edit_message_text(
                        msg, chat_id=game_flow_state['game_message_chat_id'], message_id=game_flow_state['game_message_id'],
                        reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True
                    )
                except Exception as e:
                    print(f"Error editing game over message on prompt roll: {e}")
            return
        
        # Set state to await user's dice roll
        user_game_flow_state[user_id]['state'] = 'AWAITING_USER_DICE_ROLL'
        
        # Edit the main game message to indicate waiting for user's roll
        # It's important to update the game message without the "Roll Next Round" button
        # as the user needs to send a message, not click a button.
        
        current_balance = dice_match_state.get("balance", 100.0)
        bet_amount = dice_match_state.get("bet_amount", 0)
        user_rounds = dice_match_state["user_rounds_won"]
        bot_rounds = dice_match_state["bot_rounds_won"]

        msg = (
            f"🎲 <b>Dice Match Update!</b>\n\n"
            f"<a href='tg://user?id={user_id}'>{username}</a> vs Bot\n\n"
            f"Bet: ₹{bet_amount:.2f}\n"
            f"Mode: 1 Dice, First to 2 Rounds (1d2w - Adapted)\n"
            f"Current Balance: ₹{current_balance:.2f}\n\n"
            f"Score: You {user_rounds} | Bot {bot_rounds}\n\n"
            f"<b>Please send a 🎲 dice emoji to roll your dice!</b>" # New prompt
        )
        
        # Buttons for this state: only Cashout and Back
        buttons = []
        buttons.append([InlineKeyboardButton("Cashout (Current Round)", callback_data="dice_match_cashout_mid_game")])
        buttons.append([InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")])
        reply_markup = InlineKeyboardMarkup(buttons)

        game_flow_state = user_game_flow_state[user_id]
        chat_id = game_flow_state['game_message_chat_id']
        game_message_id = game_flow_state['game_message_id']
        
        try:
            await context.bot.edit_message_text(
                msg, chat_id=chat_id, message_id=game_message_id, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True
            )
            print(f"Prompted user for dice roll successfully. Message ID: {game_message_id}")
            # Send a temporary message to confirm the prompt, which will be deleted by handle_dice_input
            temp_msg = await context.bot.send_message(chat_id=chat_id, text="Waiting for your 🎲 roll...")
            game_flow_state['temp_prompt_message_id'] = temp_msg.message_id
            print(f"Sent temp prompt message: {temp_msg.message_id}")

        except Exception as e:
            print(f"Error editing message to prompt for dice roll: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"An error occurred: {e}")
        return

    if query.data == "dice_match_cashout": # This is for initial cashout (before any rolls)
        dice_match_state = user_dice_match_state.setdefault(user_id, {})
        bet_amount = dice_match_state.get("bet_amount", 0)
        current_balance = dice_match_state.get("balance", 100.0) # Balance already has bet deducted

        current_balance += bet_amount # Refund
        user_dice_state.setdefault(user_id, {})["balance"] = current_balance

        msg = (
            f"🎲 <b>Dice Match Cashed Out!</b>\n\n"
            f"Your initial bet of ₹{bet_amount:.2f} has been refunded.\n"
            f"Final Balance: ₹{current_balance:.2f}\n"
        )
        buttons = [[InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")],
                   [InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")]]
        
        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
        if user_id in user_game_flow_state: # Clear game flow state too
            del user_game_flow_state[user_id]

        try:
            await query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True
            )
            print(f"Initial cashout message edited successfully for user {user_id}.")
        except Exception as e:
            print(f"Error editing initial cashout message for user {user_id}: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"An error occurred during cashout: {e}")

        return

    if query.data == "dice_match_cashout_mid_game": # Cashout during an ongoing match
        dice_match_state = user_dice_match_state.setdefault(user_id, {})
        bet_amount = dice_match_state.get("bet_amount", 0)
        user_rounds = dice_match_state.get("user_rounds_won", 0)
        bot_rounds = dice_match_state.get("bot_rounds_won", 0)
        current_balance = dice_match_state.get("balance", 100.0)

        win_amount = 0
        result_message = ""

        if user_rounds > bot_rounds:
            win_amount = bet_amount * (1 + (user_rounds * 0.5))
            result_message = f"Cashed out early! You partially win ₹{win_amount:.2f}."
        elif bot_rounds > user_rounds:
            win_amount = bet_amount * 0.1
            result_message = f"Cashed out early! You lost most of your bet. Refunded ₹{win_amount:.2f}."
        else:
            win_amount = bet_amount
            result_message = f"Cashed out early! Bet refunded: ₹{win_amount:.2f}."
        
        current_balance += win_amount
        user_dice_state.setdefault(user_id, {})["balance"] = current_balance
        
        msg = (
            f"🎲 <b>Dice Match Cashed Out!</b>\n\n"
            f"Final Score: You {user_rounds} | Bot {bot_rounds}\n"
            f"{result_message}\n"
            f"Final Balance: ₹{current_balance:.2f}\n"
        )
        buttons = [[InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")],
                   [InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")]]

        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
        if user_id in user_game_flow_state: # Clear game flow state too
            del user_game_flow_state[user_id]

        try:
            await query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True
            )
            print(f"Mid-game cashout message edited successfully for user {user_id}.")
        except Exception as e:
            print(f"Error editing mid-game cashout message for user {user_id}: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"An error occurred during cashout: {e}")

        return

    if query.data == "dice_match_new_game":
        # Redirect to start a new game by prompting the user with the command
        await query.message.edit_text("Starting a new Dice Match...") # Acknowledge the click
        # Ensure the user state for the game is cleared if it wasn't already by cashout/win/loss
        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
        if user_id in user_game_flow_state:
            del user_game_flow_state[user_id]

        await query.message.reply_text("Please use `/dice <mode> <amount>` to start a new match.", parse_mode="Markdown")
        return


    # --- Emojis Casino Menu ---
    if query.data == "emoji_casino":
        emoji_games_keyboard = [
            [
                InlineKeyboardButton("🔮 Predict", callback_data="game_predict"),
                InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")
            ]
        ]
        emoji_games_text = (
            "<b>Emojis Casino</b>\n\n"
            "Here you can play our provably fair and fun emojis-based games!"
        )
        await query.edit_message_text(
            emoji_games_text,
            reply_markup=InlineKeyboardMarkup(emoji_games_keyboard),
            parse_mode="HTML"
        )
        return

    elif query.data == "back_to_emoji_games":
        emoji_games_keyboard = [
            [
                InlineKeyboardButton("🔮 Predict", callback_data="game_predict"),
                InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")
            ]
        ]
        emoji_games_text = (
            "<b>Emojis Casino</b>\n\n"
            "Here you can play our provably fair and fun emojis-based games!"
        )
        await query.edit_message_text(
            emoji_games_text,
            reply_markup=InlineKeyboardMarkup(emoji_games_keyboard),
            parse_mode="HTML"
        )
        return

    elif query.data == "back_to_games":
        games_keyboard = [
            [
                InlineKeyboardButton("🎲 Emojis Casino", callback_data="emoji_casino"),
                InlineKeyboardButton("💣 Regular Games", callback_data="regular_games"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")
            ]
        ]
        games_text = (
            "<b>Games</b>\n\n"
            "Choose between emojis-based games and regular ones, all provably fair!"
        )
        await query.edit_message_text(
            games_text,
            reply_markup=InlineKeyboardMarkup(games_keyboard),
            parse_mode="HTML"
        )
        return
    elif query.data == "back_to_main":
        await start(update, context)
        return
    
    # Existing /predictions and /depositgifts handlers, which should now be in handle_button if they are InlineKeyboard callback_data
    # If these are meant to be commands, they should be handled by CommandHandler.
    # Assuming these are inline button callbacks for now:
    if query.data == "/predictions":
        # Placeholder for predictions logic
        predict_state = context.user_data.setdefault(user_id, {})
        predict_state['chosen'] = []
        predict_state['bet'] = 0.0
        predict_state['balance'] = user_predict_state.get(user_id, {}).get("balance", 100.0)
        predict_state['last_outcome'] = ""
        predict_state['last_multiplier'] = 0.0
        predict_state['last_win'] = False
        await query.edit_message_text(
            get_predict_text(predict_state),
            reply_markup=get_predict_keyboard(predict_state),
            parse_mode="HTML"
        )
        return

    if query.data == "/joingroup":
        # Placeholder for join group logic
        await query.edit_message_text("👥 Join Group: Coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]))
        return

    if query.data == "/withdraw":
        # Placeholder for withdraw logic
        await query.edit_message_text("📤 Withdraw: Coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]))
        return

    if query.data == "/depositgifts":
        # Placeholder for deposit gifts logic
        await query.edit_message_text("🎁 Deposit gifts feature coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]))
        return

    # Handlers for specific emoji games
    if query.data == "game_predict":
        predict_state = context.user_data.setdefault("predict", {})
        predict_state['chosen'] = []
        predict_state['bet'] = 0.0
        predict_state['balance'] = user_predict_state.get(user_id, {}).get("balance", 100.0)
        predict_state['last_outcome'] = ""
        predict_state['last_multiplier'] = 0.0
        predict_state['last_win'] = False
        await query.edit_message_text(
            get_predict_text(predict_state),
            reply_markup=get_predict_keyboard(predict_state),
            parse_mode="HTML"
        )
        return

    if query.data == "game_dice":
        dice_state = context.user_data.setdefault("dice", {})
        dice_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        dice_state["bet"] = 0
        dice_state["first_to"] = 3
        dice_state["rolls"] = 1
        dice_state["game"] = "dice" # Default to dice game
        dice_state["rounds_user"] = 0
        dice_state["rounds_bot"] = 0
        dice_state["last_result"] = ""
        await query.edit_message_text(
            get_dice_text(dice_state),
            reply_markup=get_dice_keyboard(dice_state),
            parse_mode="HTML"
        )
        return
    
    # Generic catch-all for unhandled callback_data
    await query.edit_message_text(f"{query.data}")


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    app = ApplicationBuilder().token('7607175238:AAEu7eI38N53gj8HkjKoUYlpuaKN4moUs3E').build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bal", balance))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("deposit", deposit)) # Handles /deposit command
    app.add_handler(CommandHandler("refer", refer)) # Handles /refer command
    app.add_handler(CommandHandler("dice", start_dice_match_command)) # Handler for the new /dice command

    # Add the new MessageHandler for dice inputs from the user
    # It will only respond to dice emojis in private chats.
    app.add_handler(MessageHandler(filters.Dice.ALL & filters.ChatType.PRIVATE, handle_dice_input))

    # Callback Query Handler (for inline keyboard button presses)
    app.add_handler(CallbackQueryHandler(handle_button))

    print("Bot is running...")
    app.run_polling()

# (Removed duplicate main block to fix indentation error)
    main()
    main()
async def start_dice_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.first_name or user.username or "Player"

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /dice <mode> <amount>\nExample: /dice 1d2w 10 (for 1 die, first to 2 rounds)")
        return

    mode = args[0]
    try:
        bet_amount = float(args[1])
        if bet_amount <= 0:
            await update.message.reply_text("Bet amount must be positive.")
            return
    except ValueError:
        await update.message.reply_text("Invalid bet amount. Please provide a number.")
        return

    current_balance = user_dice_state.get(user_id, {}).get("balance", 100.0)

    if current_balance < bet_amount:
        await update.message.reply_text(f"Insufficient balance! Your current balance is ₹{current_balance:.2f}.")
        return

    # Deduct bet at the start of the game
    current_balance -= bet_amount
    user_dice_state.setdefault(user_id, {})["balance"] = current_balance

    # Initialize state for this specific dice match game
    user_dice_match_state[user_id] = {
        "mode": mode,
        "bet_amount": bet_amount,
        "user_rounds_won": 0,
        "bot_rounds_won": 0,
        "last_user_roll": None,
        "last_bot_roll": None,
        "game_over": False,
        "final_result_message": "",
        "balance": current_balance # Store current balance for this game session
    }

    first_roller = username if random.choice([True, False]) else "Bot"
    first_roller_label = f"<a href='tg://user?id={user.id}'>{username}</a>" if first_roller == username else "Bot"

    msg = (
        f"🎲 <b>Dice Match Started!</b>\n\n"
        f"<a href='tg://user?id={user.id}'>{username}</a> vs Bot\n\n"
        f"Bet: ₹{bet_amount:.2f}\n"
        f"Mode: 1 Dice, First to 2 Rounds (1d2w - Adapted)\n" # Adjusted mode description
        f"Current Balance: ₹{current_balance:.2f}\n\n"
        f"First roller is <b>{first_roller_label}</b>."
    )

    buttons = [
        [InlineKeyboardButton(f"Roll First Round 🎲", callback_data=f"dice_match_prompt_roll")], # Changed callback_data
        [InlineKeyboardButton("Cashout (No win/loss yet)", callback_data="dice_match_cashout")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    # Store the message ID for future edits
    sent_message = await update.message.reply_text(
        msg, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True
    )
    
    # Store game message details in user_game_flow_state
    user_game_flow_state[user_id] = {
        'state': 'READY_FOR_ROLL',
        'game_message_chat_id': sent_message.chat_id,
        'game_message_id': sent_message.message_id,
        'temp_prompt_message_id': None, # No temp message yet
        'username': username # Store username for later use in handler
    }
    print(f"Game started. Stored message ID: {sent_message.message_id}")

async def handle_dice_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or update.effective_user.username or "Player"

    if user_id not in user_game_flow_state:
        print(f"Initializing user_game_flow_state for user_id: {user_id}")
        user_game_flow_state[user_id] = {
            'state': 'IDLE',  # Or some other appropriate initial state
            'game_message_chat_id': None,
            'game_message_id': None,
            'temp_prompt_message_id': None,
            'username': username
        }
    
    # Check if we are actually waiting for a dice roll from this user
    if user_id not in user_game_flow_state or user_game_flow_state[user_id]['state'] != 'AWAITING_USER_DICE_ROLL':
        print(f"Ignoring dice input from {user_id}. Not in AWAITING_USER_DICE_ROLL state.")
        # Optionally, reply to user if they sent dice outside of game flow
        # await update.message.reply_text("You can start a dice match with /dice <mode> <amount>.")
        return
    if not update.message.dice or update.message.dice.emoji != '🎲':
        await update.message.reply_text("Please send a 🎲 emoji to roll your dice.")
        return

    # User has sent their dice
    user_score = update.message.dice.value
    print(f"User {user_id} rolled: {user_score}")

    game_flow_state = user_game_flow_state[user_id]
    chat_id = game_flow_state['game_message_chat_id']
    game_message_id = game_flow_state['game_message_id']
    
    # Try to delete the temporary prompt message if it exists
    if game_flow_state['temp_prompt_message_id']:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=game_flow_state['temp_prompt_message_id'])
            print(f"Deleted temp prompt message: {game_flow_state['temp_prompt_message_id']}")
        except Exception as e:
            print(f"Could not delete temp prompt message {game_flow_state['temp_prompt_message_id']}: {e}")
        game_flow_state['temp_prompt_message_id'] = None # Reset temp message ID

    # Now, the bot rolls its dice
    await context.bot.send_message(chat_id=chat_id, text="Bot's turn:")
    bot_roll_msg = await context.bot.send_dice(chat_id=chat_id, emoji='🎲')
    print(f"Bot rolled: {bot_roll_msg.dice.value}")
    await asyncio.sleep(1.5) # Wait for animation

    bot_score = bot_roll_msg.dice.value

    # Retrieve and update dice match specific state
    dice_match_state = user_dice_match_state.setdefault(user_id, {})
    bet_amount = dice_match_state.get("bet_amount", 0)
    current_balance = dice_match_state.get("balance", 100.0)

    dice_match_state["last_user_roll"] = user_score
    dice_match_state["last_bot_roll"] = bot_score

    round_result_msg = ""
    if user_score > bot_score:
        dice_match_state["user_rounds_won"] += 1
        round_result_msg = "You win this round!"
    elif bot_score > user_score:
        dice_match_state["bot_rounds_won"] += 1
        round_result_msg = "Bot wins this round!"
    else:
        round_result_msg = "It's a draw!"

    user_rounds = dice_match_state["user_rounds_won"]
    bot_rounds = dice_match_state["bot_rounds_won"]
    print(f"Rounds won - User: {user_rounds}, Bot: {bot_rounds}")
    
    game_over = False
    final_message = ""
    win_amount = 0

    # Check for game over condition (first to 2 rounds)
    if user_rounds >= 2:
        game_over = True
        win_amount = bet_amount * 2 # Win back bet + same amount profit
        current_balance += win_amount
        final_message = f"🎉 <b>YOU WON THE MATCH!</b> You win ₹{win_amount:.2f}."
    elif bot_rounds >= 2:
        game_over = True
        final_message = f"❌ <b>BOT WON THE MATCH!</b> You lost ₹{bet_amount:.2f}."
        # Balance already deducted at start, no further change for loss.

    dice_match_state["game_over"] = game_over
    dice_match_state["final_result_message"] = final_message
    dice_match_state["balance"] = current_balance
    print(f"Game Over: {game_over}, New Balance: {current_balance}")

    user_dice_state.setdefault(user_id, {})["balance"] = current_balance

    msg = (
        f"🎲 <b>Dice Match Update!</b>\n\n"
        f"<a href='tg://user?id={user_id}'>{username}</a> vs Bot\n\n"
        f"Bet: ₹{bet_amount:.2f}\n"
        f"Mode: 1 Dice, First to 2 Rounds (1d2w - Adapted)\n" # Adjusted mode description
        f"Current Balance: ₹{current_balance:.2f}\n\n"
        f"Your Roll: <b>{user_score}</b>\n"
        f"Bot Roll: <b>{bot_score}</b>\n"
        f"<i>{round_result_msg}</i>\n\n"
        f"Score: You {user_rounds} | Bot {bot_rounds}\n"
    )
    
    buttons = []
    if game_over:
        msg += f"\n{final_message}"
        buttons.append([InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")])
        # Clear game flow state when game is over
        if user_id in user_game_flow_state:
            del user_game_flow_state[user_id]
        if user_id in user_dice_match_state: # Clear match state too
            del user_dice_match_state[user_id]
    else:
        buttons.append([InlineKeyboardButton("Roll Next Round 🎲", callback_data="dice_match_prompt_roll")])
        buttons.append([InlineKeyboardButton("Cashout (Current Round)", callback_data="dice_match_cashout_mid_game")])

    buttons.append([InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")])

    reply_markup = InlineKeyboardMarkup(buttons)
    print(f"Attempting to edit game message. Message ID: {game_message_id}, Chat ID: {chat_id}")
    try:
        await context.bot.edit_message_text(
            msg, chat_id=chat_id, message_id=game_message_id, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True
        )
        print(f"Game message edited successfully.")
    except Exception as e:
        print(f"Error editing game message {game_message_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"An error occurred: {e}")

    user_game_flow_state[user_id]['state'] = 'GAME_IN_PROGRESS' if not game_over else 'GAME_OVER'
    
    # Delete the user's dice roll message to keep chat clean (optional)
    try:
        await update.message.delete()
    except Exception as e:
        print(f"Could not delete user's dice message: {e}")

    return


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or query.from_user.username or "Player"
    await query.answer()

    # Dice Match: Handle dice match round roll
    if query.data == "dice_match_roll_round":
        match_state = user_dice_match_state.get(user_id)
        if not match_state or match_state.get("game_over"):
            await query.answer("No active match or match already finished.", show_alert=True)
            return

        # User and bot both roll dice
        user_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        match_state["last_user_roll"] = user_roll
        match_state["last_bot_roll"] = bot_roll

        # Decide round winner
        if user_roll > bot_roll:
            match_state["user_rounds_won"] += 1
            round_result = f"🎉 <b>You win this round!</b>"
        elif bot_roll > user_roll:
            match_state["bot_rounds_won"] += 1
            round_result = f"🤖 <b>Bot wins this round!</b>"
        else:
            round_result = f"🤝 <b>Draw!</b> No one gets this round."

        # Check if anyone won the match (first to 2)
        if match_state["user_rounds_won"] >= 2 or match_state["bot_rounds_won"] >= 2:
            match_state["game_over"] = True
            if match_state["user_rounds_won"] > match_state["bot_rounds_won"]:
                match_state["final_result_message"] = f"🏆 <b>You win the match!</b>\nYou won ₹{match_state['bet_amount']}!"
                # Add winnings to balance
                match_state["balance"] += match_state["bet_amount"]*2
                user_dice_state.setdefault(user_id, {})["balance"] = match_state["balance"]
            else:
                match_state["final_result_message"] = f"😢 <b>Bot wins the match!</b>\nYou lost ₹{match_state['bet_amount']}."
            match_summary = (
                f"🎲 <b>Dice Match Update</b>\n"
                f"Your Roll: <b>{user_roll}</b>\n"
                f"Bot Roll: <b>{bot_roll}</b>\n"
                f"{round_result}\n\n"
                f"Score: You {match_state['user_rounds_won']} - {match_state['bot_rounds_won']} Bot\n\n"
                f"{match_state['final_result_message']}\n"
                f"Current Balance: ₹{match_state['balance']:.2f}"
            )
            # End of game, offer to play again
            buttons = [
                [InlineKeyboardButton("Play Again", callback_data="/dice")],
                [InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")]
            ]
            await context.bot.edit_message_text(  # Use bot.edit_message_text
                chat_id=query.message.chat_id,
                message_id=user_game_flow_state[user_id]["dice_match_message_id"],  # Get message ID
                text=match_summary,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML"
            )
        else:
            # Game still running, send update and option to roll next round
            match_summary = (
                f"🎲 <b>Dice Match Update</b>\n"
                f"Your Roll: <b>{user_roll}</b>\n"
                f"Bot Roll: <b>{bot_roll}</b>\n"
                f"{round_result}\n\n"
                f"Score: You {match_state['user_rounds_won']} - {match_state['bot_rounds_won']} Bot\n"
                f"First to 2 wins.\n"
                f"Current Balance: ₹{match_state['balance']:.2f}\n\n"
                f"Ready for next round?"
            )
            buttons = [
                [InlineKeyboardButton("Roll Next Round 🎲", callback_data="dice_match_roll_round")],
                [InlineKeyboardButton("Cashout (forfeit)", callback_data="dice_match_cashout")]
            ]
            await context.bot.edit_message_text(  # Use bot.edit_message_text
                chat_id=query.message.chat_id,
                message_id=user_game_flow_state[user_id]["dice_match_message_id"],  # Get message ID
                text=match_summary,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML"
            )
        return
    # Handle /refer button
    if query.data == "/refer":
        await refer(update, context)
        return

    # Handle /deposit button from inline keyboard
    if query.data == "/deposit":
        await deposit(update, context)
        return

    # Handle /settings button
    if query.data == "/settings":
        await settings(update, context)
        return

    # Handle /games button to show the main games menu
    if query.data == "/games":
        games_keyboard = [
            [
                InlineKeyboardButton("🎲 Emojis Casino", callback_data="emoji_casino"),
                InlineKeyboardButton("💣 Regular Games", callback_data="regular_games"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")
            ]
        ]
        games_text = (
            "<b>Games</b>\n\n"
            "Choose between emojis-based games and regular ones, all provably fair!"
        )
        await query.edit_message_text(
            games_text,
            reply_markup=InlineKeyboardMarkup(games_keyboard),
            parse_mode="HTML"
        )
        return

    # Handle specific crypto button presses (if it was a ReplyKeyboardMarkup, this would be triggered by message text)
    # However, for consistency and future expansion with InlineKeyboards, we handle it here.
    # Note: When using ReplyKeyboardMarkup, the user's *message text* becomes the query.text/message.text, not query.data.
    # This part handles the case where the user *taps* a reply keyboard button, and then it's processed as a message.
    # So, we check query.message.text (which is populated when a ReplyKeyboardButton is tapped).
    if query.message and query.message.text == "USDT (BEP20)": # Ensure query.message exists
        address = "0xb7264924c0b20a0d9f1b0c5ea0e65c4d276d99cc"
        deposit_text = f"USDT (BEP20) Deposit Address:\n`{address}`\n\nSend USDT (BEP20) to the address above. Deposits are credited as soon as 1 blockchain confirmation is reached."
        deposit_keyboard = [
            [
                InlineKeyboardButton("Confirm ✅", callback_data="deposit_confirm"),
                InlineKeyboardButton("Refresh 🔄", callback_data="deposit_refresh")
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_deposit_crypto_selection")
            ]
        ]
        await query.message.reply_text(
            deposit_text,
            reply_markup=InlineKeyboardMarkup(deposit_keyboard),
            parse_mode="Markdown" # Use Markdown for code block formatting
        )
        return

    # Handlers for Confirm and Refresh deposit buttons
    if query.data == "deposit_confirm":
        await query.message.reply_text("Your deposit confirmation has been noted. Awaiting blockchain verification.")
        return
    if query.data == "deposit_refresh":
        await query.message.reply_text("Refreshing deposit status. Please wait for the blockchain to update.")
        return
    if query.data == "back_to_deposit_crypto_selection":
        await deposit(update, context) # Go back to the main deposit selection
        return


    # --- Regular Games Menu ---
    if query.data == "regular_games":
        regular_games_keyboard = [
            [
                InlineKeyboardButton("🆕🚀 Climber", callback_data="game_climber")
            ],
            [
                InlineKeyboardButton("⚡ Limbo", callback_data="game_limbo")
            ],
            [
                InlineKeyboardButton("♠️ Hilo", callback_data="game_hilo"),
                InlineKeyboardButton("💣 Mines", callback_data="game_mines")
            ],
            [
                InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
                InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack")
            ],
            [
                InlineKeyboardButton("🎯 Wheel", callback_data="game_wheel"),
                InlineKeyboardButton("🎲 Roulette", callback_data="game_roulette")
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")
            ]
        ]
        regular_games_text = (
            "<b>Regular Games</b>\n\n"
            "Not only emojis! Enjoy well-known casino games directly in your telegram app!"
        )
        await query.edit_message_text(
            regular_games_text,
            reply_markup=InlineKeyboardMarkup(regular_games_keyboard),
            parse_mode="HTML"
        )
        return

    # ----------------- SLOTS GAME (WORKING) -----------------
    if query.data == "game_slots":
        slots_state = context.user_data.setdefault("slots", {})
        slots_state["bet"] = 10
        slots_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        slots_state["last_result"] = ""
        slots_state["last_spin"] = ["❔", "❔", "❔"]
        await show_slots_game(query, context, slots_state)
        return

    if query.data == "slots_spin":
        slots_state = context.user_data.setdefault("slots", {})
        bet = slots_state.get("bet", 10)
        balance = slots_state.get("balance", 100.0)
        symbols = ["🍒", "🍋", "🍉", "⭐️", "💎", "7️⃣"]
        spin = [random.choice(symbols) for _ in range(3)]

        if balance < bet:
            slots_state["last_result"] = "Insufficient balance!"
            slots_state["last_spin"] = spin
        else:
            if spin[0] == spin[1] == spin[2]:
                win = bet * 10
                slots_state["last_result"] = f"🎉 JACKPOT! You win ₹{win}!"
                balance += win - bet
            elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
                win = bet * 2
                slots_state["last_result"] = f"Nice! You win ₹{win}!"
                balance += win - bet
            else:
                slots_state["last_result"] = f"No win. Try again!"
                balance -= bet
            slots_state["last_spin"] = spin
        slots_state["balance"] = balance
        if user_id not in user_dice_state:
            user_dice_state[user_id] = {}
        user_dice_state[user_id]["balance"] = balance
        await show_slots_game(query, context, slots_state)
        return

    # ----------------- END SLOTS GAME -----------------

    # --- Climber Game Logic ---
    if query.data == "game_climber":
        # Initialize Climber game state
        climber_state = context.user_data.setdefault("climber", {})
        climber_state["bet"] = 10
        climber_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        climber_state["cashout"] = 1.0
        climber_state["crashed"] = False
        climber_state["first_climb"] = True # Added flag for initial bet deduction
        await show_climber_game(query, context, climber_state)
        return

    if query.data == "climber_climb":
        climber_state = context.user_data.setdefault("climber", {})
        if climber_state.get("crashed"):
            await show_climber_game(query, context, climber_state)
            return

        bet = climber_state.get("bet", 10)
        current_balance = climber_state.get("balance", 100.0)

        # Deduct bet only on the very first climb of a new game round
        if climber_state.get("first_climb", True):
            if current_balance < bet:
                await query.answer("Not enough balance for the initial bet!", show_alert=True)
                return
            current_balance -= bet
            climber_state["balance"] = current_balance
            climber_state["first_climb"] = False # Mark that the initial bet has been deducted
            # Update global dice balance too
            user_dice_state.setdefault(user_id, {})["balance"] = current_balance

        cashout = climber_state.get("cashout", 1.0)
        # Each climb increases multiplier, but chance to crash increases
        cashout = round(cashout * random.uniform(1.1, 2.0), 2)
        crash_chance = min(0.15 + (cashout-1.0)*0.13, 0.8) # crash risk increases
        crashed = random.random() < crash_chance
        
        climber_state["cashout"] = cashout
        climber_state["crashed"] = crashed
        
        await show_climber_game(query, context, climber_state)
        return

    if query.data == "climber_cashout":
        climber_state = context.user_data.setdefault("climber", {})
        bet = climber_state.get("bet", 10)
        cashout = climber_state.get("cashout", 1.0)
        balance = climber_state.get("balance", 100.0) # This balance already has the initial bet deducted

        # If user cashed out immediately without clicking "Climb" (i.e., first_climb is still True)
        if climber_state.get("first_climb", True):
            # This scenario means they tried to cashout before any actual game play.
            # Refund the initial bet if it was deducted. Or, if no bet was deducted, no win/loss.
            climber_state["last_result"] = "Game not started. No win/loss."
            climber_state["crashed"] = True # End the game
            win = 0
        else:
            win = round(bet * cashout, 2)
            balance = balance + win # Add win to the balance (which already had the bet deducted)
            climber_state["last_result"] = f"<b>CASHED OUT</b> at <b>{cashout:.2f}x</b>! You win <b>₹{win:.2f}</b>!"
            climber_state["crashed"] = True # End the game

        climber_state["balance"] = balance
        # Update global dice balance too
        user_dice_state.setdefault(user_id, {})["balance"] = balance

        await query.edit_message_text(
            f"🆕🚀 <b>Climber</b>\n\n{climber_state['last_result']}\n\nBalance: ₹{balance:.2f}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Play Again", callback_data="game_climber")],
                [InlineKeyboardButton("⬅️ Back", callback_data="regular_games")]
            ]),
            parse_mode="HTML"
        )
        return

    # --- LIMBO GAME LOGIC ---
    if query.data == "game_limbo":
        limbo_state = context.user_data.setdefault("limbo", {})
        limbo_state["target"] = 2.0
        limbo_state["bet"] = 10
        limbo_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        limbo_state["last_result"] = ""
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_target_up":
        limbo_state = context.user_data.setdefault("limbo", {})
        limbo_state["target"] = min(round(limbo_state.get("target", 2.0) + 0.1, 2), 10.0)
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_target_down":
        limbo_state = context.user_data.setdefault("limbo", {})
        limbo_state["target"] = max(round(limbo_state.get("target", 2.0) - 0.1, 2), 1.01)
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_bet":
        limbo_state = context.user_data.setdefault("limbo", {})
        bet = limbo_state.get("bet", 10)
        # Simple bet cycling (10 -> 50 -> 100 -> 10)
        limbo_state["bet"] = {10: 50, 50: 100, 100: 10}.get(bet, 10)
        await show_limbo_game(query, context, limbo_state)
        return

    if query.data == "limbo_play":
        limbo_state = context.user_data.setdefault("limbo", {})
        bet = limbo_state.get("bet", 10)
        balance = limbo_state.get("balance", 100.0)
        target = limbo_state.get("target", 2.0)
        if bet > balance:
            limbo_state["last_result"] = "<b>Insufficient balance!</b>"
            await show_limbo_game(query, context, limbo_state)
            return

        payout = random.uniform(1.0, 10.0)
        if payout >= target:
            win = round(bet * target, 2)
            limbo_state["last_result"] = f"🎉 <b>WIN!</b> Multiplier: <b>{payout:.2f}x</b>\nYou won ₹{win}!"
            limbo_state["balance"] = round(balance - bet + win, 2)
        else:
            limbo_state["last_result"] = f"❌ <b>LOST!</b> Multiplier: <b>{payout:.2f}x</b>\nYou lost ₹{bet}!"
            limbo_state["balance"] = round(balance - bet, 2)

        # Also update global dice balance for consistency
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = limbo_state["balance"]

        await show_limbo_game(query, context, limbo_state)
        return

    # --- HILO GAME LOGIC ---
    if query.data == "game_hilo":
        hilo_state = context.user_data.setdefault("hilo", {})
        hilo_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        hilo_state["bet"] = 10
        hilo_state["card"] = None
        hilo_state["last_result"] = ""
        await show_hilo_game(query, context, hilo_state)
        return

    if query.data == "hilo_higher" or query.data == "hilo_lower":
        hilo_state = context.user_data.setdefault("hilo", {})
        bet = hilo_state.get("bet", 10)
        balance = hilo_state.get("balance", 100.0)
        card = hilo_state.get("card", None)
        if card is None:
            await show_hilo_game(query, context, hilo_state)
            return
        # Draw a new card
        next_card = random.randint(2, 14)
        if query.data == "hilo_higher":
            win = next_card > card
        else:
            win = next_card < card
        if card == next_card:
            # Draw, refund
            hilo_state["last_result"] = f"Draw! Next card was {hilo_card_emoji(next_card)}. Your bet is refunded."
            hilo_state["balance"] = balance
        elif win:
            win_amt = bet * 1.95
            hilo_state["last_result"] = f"🎉 WIN! Next card was {hilo_card_emoji(next_card)}. You won ₹{win_amt:.2f}!"
            hilo_state["balance"] = balance + win_amt
        else:
            hilo_state["last_result"] = f"❌ LOST! Next card was {hilo_card_emoji(next_card)}. You lost ₹{bet}."
            hilo_state["balance"] = balance - bet
        hilo_state["bet"] = 10
        hilo_state["card"] = None
        # Also update the global dice balance for consistency
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = hilo_state["balance"]
        await show_hilo_game(query, context, hilo_state)
        return

    # --- MINES GAME LOGIC ---
    if query.data == "game_mines":
        mines_state = context.user_data.setdefault("mines", {})
        mines_state["bet"] = 10
        mines_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        # Randomly place 3 mines
        grid = [0]*9
        for i in random.sample(range(9), 3):
            grid[i] = 1
        mines_state["grid"] = grid
        mines_state["revealed"] = [False]*9
        mines_state["last_result"] = ""
        mines_state["safe_revealed"] = 0
        mines_state["game_started"] = False # Reset game_started flag
        await show_mines_game(query, context, mines_state)
        return

    if query.data.startswith("mines_reveal_"):
        idx = int(query.data.split("_")[-1])
        mines_state = context.user_data.setdefault("mines", {})
        bet = mines_state.get("bet", 10)
        balance = mines_state.get("balance", 100.0)
        grid = mines_state.get("grid", [0]*9)
        revealed = mines_state.get("revealed", [False]*9)
        
        if revealed[idx]: # If already revealed, do nothing but refresh
            await query.answer("Tile already revealed!", show_alert=True)
            await show_mines_game(query, context, mines_state)
            return

        # Deduct bet on first reveal for Mines game.
        if mines_state.get("game_started", False) == False:
            if balance < bet:
                mines_state["last_result"] = "<b>Insufficient balance for this bet!</b>"
                await show_mines_game(query, context, mines_state)
                return
            balance -= bet
            mines_state["balance"] = balance
            mines_state["game_started"] = True # Mark game as started

        revealed[idx] = True
        if grid[idx]:  # Hit a mine
            mines_state["last_result"] = "Boom! You hit a mine. Lost bet."
            mines_state["revealed"] = [True if g else revealed[i] for i, g in enumerate(grid)] # Reveal all mines on game over
            mines_state["safe_revealed"] = 0 # Reset for next game
            mines_state["game_started"] = False # Reset game state for next round
        else: # Safe tile
            mines_state["safe_revealed"] = mines_state.get("safe_revealed", 0) + 1
            mines_state["last_result"] = f"Safe! {mines_state['safe_revealed']} revealed."
            mines_state["revealed"] = revealed
        
        # Update global dice balance for consistency
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        
        await show_mines_game(query, context, mines_state)
        return

    if query.data == "mines_cashout":
        mines_state = context.user_data.setdefault("mines", {})
        safe = mines_state.get("safe_revealed", 0)
        bet = mines_state.get("bet", 10)
        balance = mines_state.get("balance", 100.0)

        # If game was not started (no tiles revealed yet) and user tries to cashout
        if mines_state.get("game_started", False) == False:
            mines_state["last_result"] = "Game not started. No win/loss."
            # No change to balance if bet wasn't deducted
            final_balance = balance
        else: # Game was started and tiles were revealed
            profit = (bet * safe * 0.5) # This is the profit from safe tiles
            final_balance = balance + profit # Add profit to current balance (which already had initial bet deducted)
            mines_state["last_result"] = f"Cashed out! You win ₹{profit:.2f} profit." # Profit is the amount above the bet

        mines_state["balance"] = final_balance
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = final_balance
        
        # Reset game state for next round
        mines_state["safe_revealed"] = 0 
        mines_state["revealed"] = [False]*9 
        mines_state["game_started"] = False
        # Randomly place new mines for the next game display
        grid = [0]*9
        for i in random.sample(range(9), 3):
            grid[i] = 1
        mines_state["grid"] = grid

        await show_mines_game(query, context, mines_state)
        return
    
    # ----------------- BLACKJACK GAME (NEW) -----------------
    if query.data == "game_blackjack":
        bj_state = context.user_data.setdefault("bj", {})
        bj_state["bet"] = 10
        bj_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        
        # Deduct bet at the start of the Blackjack game
        if bj_state["balance"] < bj_state["bet"]:
            await query.answer("Insufficient balance to start Blackjack!", show_alert=True)
            return
        bj_state["balance"] -= bj_state["bet"]
        user_dice_state.setdefault(user_id, {})["balance"] = bj_state["balance"] # Update global balance

        bj_state["player"] = [draw_card(), draw_card()]
        bj_state["dealer"] = [draw_card(), draw_card()]
        bj_state["last_result"] = ""
        await show_blackjack_game(query, context, bj_state)
        return

    if query.data == "bj_hit":
        bj_state = context.user_data.setdefault("bj", {})
        if hand_value(bj_state["player"]) >= 21: # Prevent hitting if already 21 or busted
            await query.answer("Cannot hit!", show_alert=True)
            await show_blackjack_game(query, context, bj_state)
            return
        
        bj_state["player"].append(draw_card())
        
        # Check if busted immediately after hitting
        if hand_value(bj_state["player"]) > 21:
            bj_state["last_result"] = f"❌ Busted! You lose ₹{bj_state['bet']}."
            # Balance already deducted at start, no further change for loss.
            # No need to add back bet, it's a loss.
            # Reset state for next game, but don't reset balance
        
        await show_blackjack_game(query, context, bj_state)
        return

    if query.data == "bj_stand":
        bj_state = context.user_data.setdefault("bj", {})
        player_val = hand_value(bj_state["player"])
        dealer = bj_state["dealer"]
        bet = bj_state.get("bet", 10)
        balance = bj_state.get("balance", 100.0) # This balance already has the initial bet deducted
        
        # Dealer draws cards until 17 or more
        while hand_value(dealer) < 17:
            dealer.append(draw_card())
            
        dealer_val = hand_value(dealer)

        # Determine game result and update balance
        win_amount = 0
        if player_val > 21:
            bj_state["last_result"] = f"❌ Busted! You lose ₹{bet}."
            # Balance already deducted, nothing to add/subtract.
        elif dealer_val > 21:
            win_amount = bet * 2
            bj_state["last_result"] = f"🎉 Dealer busted! Dealer hand: {', '.join(dealer)} ({dealer_val}). You win ₹{win_amount}."
            balance += win_amount
        elif player_val > dealer_val:
            win_amount = bet * 2
            bj_state["last_result"] = f"🎉 You win! Dealer hand: {', '.join(dealer)} ({dealer_val}). Win ₹{win_amount}."
            balance += win_amount
        elif player_val == dealer_val:
            win_amount = bet # Refund the bet
            bj_state["last_result"] = f"Draw! Dealer hand: {', '.join(dealer)} ({dealer_val}). Bet refunded."
            balance += win_amount # Add back the refunded bet
        else:
            bj_state["last_result"] = f"❌ Dealer wins with {', '.join(dealer)} ({dealer_val})! You lose ₹{bet}."
            # Balance already deducted, nothing to add/subtract.
            
        bj_state["balance"] = balance
        # Update global user balance
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        await show_blackjack_game(query, context, bj_state)
        return
    # ----------------- END BLACKJACK GAME -----------------

    # ----------------- WHEEL GAME (NEW) -----------------
    if query.data == "game_wheel":
        wheel_state = context.user_data.setdefault("wheel", {})
        wheel_state["bet"] = 10
        wheel_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        wheel_state["last_result"] = ""
        await show_wheel_game(query, context, wheel_state)
        return

    if query.data == "wheel_spin":
        wheel_state = context.user_data.setdefault("wheel", {})
        bet = wheel_state.get("bet", 10)
        balance = wheel_state.get("balance", 100.0)
        segments = [2, 3, 5, 10, 20, 50, 0, 0, 0] # Values to win, 0 for loss
        
        if balance < bet:
            wheel_state["last_result"] = "Insufficient balance!"
        else:
            # Deduct bet before spin
            balance -= bet
            result = random.choice(segments)
            if result == 0:
                wheel_state["last_result"] = f"No win. Try again!"
            else:
                win = bet * result
                wheel_state["last_result"] = f"🎉 You win {result}x! Payout: ₹{win}."
                balance += win # Add win to balance after deducting bet
        
        wheel_state["balance"] = balance
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        await show_wheel_game(query, context, wheel_state)
        return
    # ----------------- END WHEEL GAME -----------------

    # ----------------- ROULETTE GAME (NEW) -----------------
    if query.data == "game_roulette":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["bet"] = 10
        roulette_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        roulette_state["last_result"] = ""
        roulette_state["color_bet"] = None
        roulette_state["num_bet"] = None
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_red":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["color_bet"] = "red"
        roulette_state["num_bet"] = None
        roulette_state["last_result"] = "Bet placed on RED."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_black":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["color_bet"] = "black"
        roulette_state["num_bet"] = None
        roulette_state["last_result"] = "Bet placed on BLACK."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_green":
        roulette_state = context.user_data.setdefault("roulette", {})
        roulette_state["color_bet"] = "green"
        roulette_state["num_bet"] = None
        roulette_state["last_result"] = "Bet placed on GREEN (0)."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_bet_number":
        roulette_state = context.user_data.setdefault("roulette", {})
        # For simplicity, always bet on 7 (you can ask user for input)
        roulette_state["num_bet"] = 7
        roulette_state["color_bet"] = None
        roulette_state["last_result"] = "Bet placed on NUMBER 7."
        await show_roulette_game(query, context, roulette_state)
        return

    if query.data == "roulette_spin":
        roulette_state = context.user_data.setdefault("roulette", {})
        bet = roulette_state.get("bet", 10)
        balance = roulette_state.get("balance", 100.0)
        color_bet = roulette_state.get("color_bet", None)
        num_bet = roulette_state.get("num_bet", None)
        
        if not (color_bet or num_bet):
            roulette_state["last_result"] = "Please place a bet (color or number) before spinning!"
            await show_roulette_game(query, context, roulette_state)
            return

        if balance < bet:
            roulette_state["last_result"] = "Insufficient balance!"
            await show_roulette_game(query, context, roulette_state)
            return

        # Deduct bet before spin
        balance -= bet

        result = random.randint(0, 36)
        if result == 0:
            result_color = "green"
        elif result % 2 == 0: # European roulette, 1-10, 19-28 red (odd), black (even). 11-18, 29-36 black (odd), red (even)
            # For simplicity, let's just assume even numbers are black, odd are red (except 0 green)
            result_color = "black"
        else:
            result_color = "red"
        
        msg = f"Result: <b>{result} ({result_color.title()})</b>\n"
        
        win_amount = 0
        if color_bet and color_bet == result_color:
            win_amount = bet * (14 if result_color == "green" else 2)
            msg += f"🎉 You win ₹{win_amount}!"
            balance += win_amount
        elif num_bet is not None and result == num_bet:
            win_amount = bet * 36
            msg += f"🎉 You win ₹{win_amount}!"
            balance += win_amount
        else:
            msg += "Lost the bet."
        
        roulette_state["balance"] = balance
        roulette_state["last_result"] = msg
        user_dice_state.setdefault(user_id, {})
        user_dice_state[user_id]["balance"] = balance
        await show_roulette_game(query, context, roulette_state)
        return
    # ----------------- END ROULETTE GAME -----------------

    # ----------------- DICE MATCH GAME (UPDATED FLOW) -----------------
    if query.data == "dice_match_prompt_roll": # Triggered by "Roll First/Next Round" button
        print(f"Entering dice_match_prompt_roll for user {user_id}")
        dice_match_state = user_dice_match_state.setdefault(user_id, {})
        if dice_match_state.get("game_over", False):
            await query.answer("Game is over. Start a new one with /dice.", show_alert=True)
            # Revert buttons to new game
            if user_id in user_game_flow_state:
                game_flow_state = user_game_flow_state[user_id]
                msg = (
                    f"🎲 <b>Dice Match Ended!</b>\n\n"
                    f"{dice_match_state.get('final_result_message', 'Game has ended.')}\n"
                    f"Final Balance: ₹{dice_match_state.get('balance', 100.0):.2f}\n"
                )
                buttons = [[InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")],
                           [InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")]]
                try:
                    await context.bot.edit_message_text(
                        msg, chat_id=game_flow_state['game_message_chat_id'], message_id=game_flow_state['game_message_id'],
                        reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True
                    )
                except Exception as e:
                    print(f"Error editing game over message on prompt roll: {e}")
            return
        
        # Set state to await user's dice roll
        user_game_flow_state[user_id]['state'] = 'AWAITING_USER_DICE_ROLL'
        
        # Edit the main game message to indicate waiting for user's roll
        # It's important to update the game message without the "Roll Next Round" button
        # as the user needs to send a message, not click a button.
        
        current_balance = dice_match_state.get("balance", 100.0)
        bet_amount = dice_match_state.get("bet_amount", 0)
        user_rounds = dice_match_state["user_rounds_won"]
        bot_rounds = dice_match_state["bot_rounds_won"]

        msg = (
            f"🎲 <b>Dice Match Update!</b>\n\n"
            f"<a href='tg://user?id={user_id}'>{username}</a> vs Bot\n\n"
            f"Bet: ₹{bet_amount:.2f}\n"
            f"Mode: 1 Dice, First to 2 Rounds (1d2w - Adapted)\n"
            f"Current Balance: ₹{current_balance:.2f}\n\n"
            f"Score: You {user_rounds} | Bot {bot_rounds}\n\n"
            f"<b>Please send a 🎲 dice emoji to roll your dice!</b>" # New prompt
        )
        
        # Buttons for this state: only Cashout and Back
        buttons = []
        buttons.append([InlineKeyboardButton("Cashout (Current Round)", callback_data="dice_match_cashout_mid_game")])
        buttons.append([InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")])
        reply_markup = InlineKeyboardMarkup(buttons)

        game_flow_state = user_game_flow_state[user_id]
        chat_id = game_flow_state['game_message_chat_id']
        game_message_id = game_flow_state['game_message_id']
        
        try:
            await context.bot.edit_message_text(
                msg, chat_id=chat_id, message_id=game_message_id, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True
            )
            print(f"Prompted user for dice roll successfully. Message ID: {game_message_id}")
            # Send a temporary message to confirm the prompt, which will be deleted by handle_dice_input
            temp_msg = await context.bot.send_message(chat_id=chat_id, text="Waiting for your 🎲 roll...")
            game_flow_state['temp_prompt_message_id'] = temp_msg.message_id
            print(f"Sent temp prompt message: {temp_msg.message_id}")

        except Exception as e:
            print(f"Error editing message to prompt for dice roll: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"An error occurred: {e}")
        return

    if query.data == "dice_match_cashout": # This is for initial cashout (before any rolls)
        dice_match_state = user_dice_match_state.setdefault(user_id, {})
        bet_amount = dice_match_state.get("bet_amount", 0)
        current_balance = dice_match_state.get("balance", 100.0) # Balance already has bet deducted

        current_balance += bet_amount # Refund
        user_dice_state.setdefault(user_id, {})["balance"] = current_balance

        msg = (
            f"🎲 <b>Dice Match Cashed Out!</b>\n\n"
            f"Your initial bet of ₹{bet_amount:.2f} has been refunded.\n"
            f"Final Balance: ₹{current_balance:.2f}\n"
        )
        buttons = [[InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")],
                   [InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")]]
        
        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
        if user_id in user_game_flow_state: # Clear game flow state too
            del user_game_flow_state[user_id]

        try:
            await query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True
            )
            print(f"Initial cashout message edited successfully for user {user_id}.")
        except Exception as e:
            print(f"Error editing initial cashout message for user {user_id}: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"An error occurred during cashout: {e}")

        return

    if query.data == "dice_match_cashout_mid_game": # Cashout during an ongoing match
        dice_match_state = user_dice_match_state.setdefault(user_id, {})
        bet_amount = dice_match_state.get("bet_amount", 0)
        user_rounds = dice_match_state.get("user_rounds_won", 0)
        bot_rounds = dice_match_state.get("bot_rounds_won", 0)
        current_balance = dice_match_state.get("balance", 100.0)

        win_amount = 0
        result_message = ""

        if user_rounds > bot_rounds:
            win_amount = bet_amount * (1 + (user_rounds * 0.5))
            result_message = f"Cashed out early! You partially win ₹{win_amount:.2f}."
        elif bot_rounds > user_rounds:
            win_amount = bet_amount * 0.1
            result_message = f"Cashed out early! You lost most of your bet. Refunded ₹{win_amount:.2f}."
        else:
            win_amount = bet_amount
            result_message = f"Cashed out early! Bet refunded: ₹{win_amount:.2f}."
        
        current_balance += win_amount
        user_dice_state.setdefault(user_id, {})["balance"] = current_balance
        
        msg = (
            f"🎲 <b>Dice Match Cashed Out!</b>\n\n"
            f"Final Score: You {user_rounds} | Bot {bot_rounds}\n"
            f"{result_message}\n"
            f"Final Balance: ₹{current_balance:.2f}\n"
        )
        buttons = [[InlineKeyboardButton("Play New Match", callback_data="dice_match_new_game")],
                   [InlineKeyboardButton("⬅️ Back to Regular Games", callback_data="regular_games")]]

        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
        if user_id in user_game_flow_state: # Clear game flow state too
            del user_game_flow_state[user_id]

        try:
            await query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML", disable_web_page_preview=True
            )
            print(f"Mid-game cashout message edited successfully for user {user_id}.")
        except Exception as e:
            print(f"Error editing mid-game cashout message for user {user_id}: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"An error occurred during cashout: {e}")

        return

    if query.data == "dice_match_new_game":
        # Redirect to start a new game by prompting the user with the command
        await query.message.edit_text("Starting a new Dice Match...") # Acknowledge the click
        # Ensure the user state for the game is cleared if it wasn't already by cashout/win/loss
        if user_id in user_dice_match_state:
            del user_dice_match_state[user_id]
        if user_id in user_game_flow_state:
            del user_game_flow_state[user_id]

        await query.message.reply_text("Please use `/dice <mode> <amount>` to start a new match.", parse_mode="Markdown")
        return


    # --- Emojis Casino Menu ---
    if query.data == "emoji_casino":
        emoji_games_keyboard = [
            [
                InlineKeyboardButton("🔮 Predict", callback_data="game_predict"),
                InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")
            ]
        ]
        emoji_games_text = (
            "<b>Emojis Casino</b>\n\n"
            "Here you can play our provably fair and fun emojis-based games!"
        )
        await query.edit_message_text(
            emoji_games_text,
            reply_markup=InlineKeyboardMarkup(emoji_games_keyboard),
            parse_mode="HTML"
        )
        return

    elif query.data == "back_to_emoji_games":
        emoji_games_keyboard = [
            [
                InlineKeyboardButton("🔮 Predict", callback_data="game_predict"),
                InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_games")
            ]
        ]
        emoji_games_text = (
            "<b>Emojis Casino</b>\n\n"
            "Here you can play our provably fair and fun emojis-based games!"
        )
        await query.edit_message_text(
            emoji_games_text,
            reply_markup=InlineKeyboardMarkup(emoji_games_keyboard),
            parse_mode="HTML"
        )
        return

    elif query.data == "back_to_games":
        games_keyboard = [
            [
                InlineKeyboardButton("🎲 Emojis Casino", callback_data="emoji_casino"),
                InlineKeyboardButton("💣 Regular Games", callback_data="regular_games"),
            ],
            [
                InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")
            ]
        ]
        games_text = (
            "<b>Games</b>\n\n"
            "Choose between emojis-based games and regular ones, all provably fair!"
        )
        await query.edit_message_text(
            games_text,
            reply_markup=InlineKeyboardMarkup(games_keyboard),
            parse_mode="HTML"
        )
        return
    elif query.data == "back_to_main":
        await start(update, context)
        return
    
    # Existing /predictions and /depositgifts handlers, which should now be in handle_button if they are InlineKeyboard callback_data
    # If these are meant to be commands, they should be handled by CommandHandler.
    # Assuming these are inline button callbacks for now:
    if query.data == "/predictions":
        # Placeholder for predictions logic
        predict_state = context.user_data.setdefault(user_id, {})
        predict_state['chosen'] = []
        predict_state['bet'] = 0.0
        predict_state['balance'] = user_predict_state.get(user_id, {}).get("balance", 100.0)
        predict_state['last_outcome'] = ""
        predict_state['last_multiplier'] = 0.0
        predict_state['last_win'] = False
        await query.edit_message_text(
            get_predict_text(predict_state),
            reply_markup=get_predict_keyboard(predict_state),
            parse_mode="HTML"
        )
        return

    if query.data == "/joingroup":
        # Placeholder for join group logic
        await query.edit_message_text("👥 Join Group: Coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]))
        return

    if query.data == "/withdraw":
        # Placeholder for withdraw logic
        await query.edit_message_text("📤 Withdraw: Coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]))
        return

    if query.data == "/depositgifts":
        # Placeholder for deposit gifts logic
        await query.edit_message_text("🎁 Deposit gifts feature coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ BACK", callback_data="back_to_main")]]))
        return

    # Handlers for specific emoji games
    if query.data == "game_predict":
        predict_state = context.user_data.setdefault("predict", {})
        predict_state['chosen'] = []
        predict_state['bet'] = 0.0
        predict_state['balance'] = user_predict_state.get(user_id, {}).get("balance", 100.0)
        predict_state['last_outcome'] = ""
        predict_state['last_multiplier'] = 0.0
        predict_state['last_win'] = False
        await query.edit_message_text(
            get_predict_text(predict_state),
            reply_markup=get_predict_keyboard(predict_state),
            parse_mode="HTML"
        )
        return

    if query.data == "game_dice":
        dice_state = context.user_data.setdefault("dice", {})
        dice_state["balance"] = user_dice_state.get(user_id, {}).get("balance", 100.0)
        dice_state["bet"] = 0
        dice_state["first_to"] = 3
        dice_state["rolls"] = 1
        dice_state["game"] = "dice" # Default to dice game
        dice_state["rounds_user"] = 0
        dice_state["rounds_bot"] = 0
        dice_state["last_result"] = ""
        await query.edit_message_text(
            get_dice_text(dice_state),
            reply_markup=get_dice_keyboard(dice_state),
            parse_mode="HTML"
        )
        return
    
    # Generic catch-all for unhandled callback_data
    await query.edit_message_text(f"{query.data}")


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    app = ApplicationBuilder().token('7607175238:AAEu7eI38N53gj8HkjKoUYlpuaKN4moUs3E').build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bal", balance))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("deposit", deposit)) # Handles /deposit command
    app.add_handler(CommandHandler("refer", refer)) # Handles /refer command
    app.add_handler(CommandHandler("dice", start_dice_match_command)) # Handler for the new /dice command

    # Add the new MessageHandler for dice inputs from the user
    # It will only respond to dice emojis in private chats.
    app.add_handler(MessageHandler(filters.Dice.ALL & filters.ChatType.PRIVATE, handle_dice_input))

    # Callback Query Handler (for inline keyboard button presses)
    app.add_handler(CallbackQueryHandler(handle_button))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
