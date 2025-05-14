import random
import time
from collections import Counter
from itertools import combinations

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

# my card representation: 0-51, where card = 13 * suit_index + rank_index
def card_to_str(card):
    return RANKS[card % 13] + SUITS[card // 13]

def get_deck():
    return list(range(52))

def shuffle_deck(exclude_cards=None):
    deck = get_deck()
    
    if exclude_cards:
        filtered_deck = []
        for card in deck:
            if card not in exclude_cards:
                filtered_deck.append(card)
        deck = filtered_deck
        
    random.shuffle(deck)
    return deck

def deal_cards(deck, num):
    dealt = deck[:num]
    return dealt, deck[num:]

# evaluates best 5 cards hand from 7 cards, returns tuple w hand rank and tiebreaker vals
# so like higher tuple is better hand w texas holdem hand rules
def evaluate_hand(cards):
    ranks = [card % 13 for card in cards]
    suits = [card // 13 for card in cards]
    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)
            
    # a general Flush -> same suit
    flush_suit = None
    for suit, count in suit_counts.items():
        if count >= 5:
            flush_suit = suit
            break

    flush_ranks = []
    if flush_suit is not None:
        for card in cards:
            if card // 13 == flush_suit:
                rank = card % 13
                flush_ranks.append(rank)

        flush_ranks.sort(reverse=True) #ranks decending

    # a general Straight -> 5 consecutive cards
    straight_high = get_straight_highest_card(ranks)
    flush_straight_high = get_straight_highest_card(flush_ranks) if flush_ranks else -1

    # Royal Flush
    if flush_straight_high == 12:
        return (9,)
    
    # Straight flush (w highest card for tie breaking)
    if flush_straight_high != -1:
        return (8, flush_straight_high)

    # Four of a Kind
    for rank, count in rank_counts.items():
        if count == 4:
            potential_kickers = []
            for r in ranks:
                if r != rank:
                    potential_kickers.append(r)
            kicker = max(potential_kickers) #highest remaining card
            return (7, rank, kicker)

    # Full house -> 3 cards same, 2 cards same
    triples = []
    for r, c in rank_counts.items():
        if c == 3:
            triples.append(r)
    pairs = []
    for r, c in rank_counts.items():
        if c == 2:
            pairs.append(r)
            
    if triples:
        triple = max(triples)
        remaining = triples + pairs
        remaining = [r for r in remaining if r != triple] #excluding the triples from the pairs
        if remaining:
            return (6, triple, max(remaining))

    # Flush
    if flush_ranks:
        return (5,) + tuple(flush_ranks[:5])

    # Straight
    if straight_high != -1:
        return (4, straight_high)

    # Three of a Kind
    if triples:
        triple = max(triples)
        potential_kickers = []
        for r in ranks:
            if r != triple:
                potential_kickers.append(r)
        kickers = sorted(potential_kickers, reverse=True)
        return (3, triple, kickers[0], kickers[1])
    
    # Two Pair
    if len(pairs) >= 2:
        top_two = sorted(pairs, reverse=True)[:2]
        potential_kickers = []
        for r in ranks:
            if r not in top_two:
                potential_kickers.append(r)
        kicker = max(potential_kickers)
        
        return (2, top_two[0], top_two[1], kicker)

    # One pair
    if pairs:
        pair = max(pairs)
        potential_kickers = []
        for r in ranks:
            if r != pair:
                potential_kickers.append(r)
        kickers = sorted(potential_kickers, reverse=True)

        return (1, pair) + tuple(kickers[:3])

    # High card
    sorted_ranks = sorted(ranks, reverse=True)
    return (0,) + tuple(sorted_ranks[:5])


def get_straight_highest_card(ranks): # highest card in straight, or -1 if no straight
    rank_set = set(ranks)
    
    for high in range(12, 3, -1): #lowest straight would start at 4
        straight_found = True
        
        for i in range(5):
            expected_card = (high - i) % 13
            if expected_card not in rank_set:
                straight_found = False
                break
        if straight_found:
            return high
        
    if {12, 0, 1, 2, 3}.issubset(rank_set): #edge case for 5432A
        return 3
    
    return -1 #no straight found

# MCTS algo, ucb1 wasn't needed
def estimate_win_rate(my_hole, community_cards):
    start_time = time.time()
    wins = 0
    losses = 0
    ties = 0
    total = 0

    known_cards = set(my_hole + community_cards)
    
    # estimate win probability by running as many simulated games in 10sec
    while time.time() - start_time < 10.0:
        deck = shuffle_deck(exclude_cards=known_cards)
        
        # simulating opponent hole cards cuz we dont know
        opp_hole, deck = deal_cards(deck, 2) #updating deck for community

        # simulating future community cards
        future_community, deck = deal_cards(deck, 5 - len(community_cards))
        full_community = community_cards + future_community

        # print(my_hole + full_community)
        my_score = evaluate_hand(my_hole + full_community)
        opp_score = evaluate_hand(opp_hole + full_community)

        if my_score > opp_score:
            wins += 1
        elif my_score < opp_score:
            losses += 1
        else:
            ties += 1
        total += 1

    win_rate = ((wins + (0.5 * ties)) / total) if total > 0 else 0
    return win_rate, total

def make_decision(my_hole, community_cards):
    #stay or fold based on estimated win prob
    win_rate, simulations_ran = estimate_win_rate(my_hole, community_cards)
    decision = "STAY" if win_rate >= 0.5 else "FOLD"
    
    print(f"[Decision Point] Hole: {[card_to_str(c) for c in my_hole]} | Community: {[card_to_str(c) for c in community_cards]}")
    print(f"- Estimated Win Rate: {100.0 * win_rate:.3f}% over {simulations_ran} simulations")
    print(f"- Decision: {decision}")
    return decision

def play_hand():
    full_deck = get_deck()
    random.shuffle(full_deck)

    my_hole = full_deck[:2]
    print("My Hole Cards:", [card_to_str(c) for c in my_hole], "\n")
    opp_hole = full_deck[2:4] #duran said not used by bot, passive
    remaining_deck = full_deck[4:]

    # Decision 1: Pre-Flop (no community cards yet)
    community_cards = []
    decision = make_decision(my_hole, community_cards)
    if decision == "FOLD":
        print("Bot folded Pre-Flop\n")
        return

    # Reveal Flop (3 cards)
    flop = remaining_deck[:3]
    community_cards += flop
    print("\nFLOP, 3 Community Cards:", [card_to_str(c) for c in community_cards], "\n")
    remaining_deck = remaining_deck[3:]

    # Decision 2: Pre-Turn
    decision = make_decision(my_hole, community_cards)
    if decision == "FOLD":
        print("Bot folded Pre-Turn\n")
        return

    # Reveal Turn (1 card)
    turn = remaining_deck[:1]
    community_cards += turn
    print("\nTURN, 1 Additional Community Card:", [card_to_str(c) for c in community_cards], "\n")
    remaining_deck = remaining_deck[1:]

    # Decision 3: Pre-River
    decision = make_decision(my_hole, community_cards)
    if decision == "FOLD":
        print("Bot folded Pre-River\n")
        return

    # Reveal River (1 card)
    river = remaining_deck[:1]
    community_cards += river
    print("\nRIVER, 1 Final Community Card:", [card_to_str(c) for c in community_cards], "\n")

    print("Bot stayed until the River")
    print(f"Final Board (All Community Cards): {[card_to_str(c) for c in community_cards]}")

    print("\nShowdown!")
    my_final = evaluate_hand(my_hole + community_cards)
    opp_final = evaluate_hand(opp_hole + community_cards)
    print(f"Bot Hand: {[card_to_str(c) for c in my_hole]} -> {my_final}")
    print(f"Opponent Hand: {[card_to_str(c) for c in opp_hole]} -> {opp_final}\n")

    if my_final > opp_final:
        print("Bot WINS!\n")
    elif my_final < opp_final:
        print("Bot LOSES!\n")
    else:
        print("It's a TIE!\n")

if __name__ == "__main__":
    play_hand()
