# ====================================================
# RANDOM DEMO AMOUNT
# ====================================================

opening_text = (
    f"AI TRADING EXAMPLE\\: ${short_amount} EVERY DAY"
)

# ====================================================
# OPENING TEXT — FIRST 3 SECONDS
# ====================================================

# LINE 1
"drawtext="
"fontfile=/usr/share/fonts/truetype/"
"dejavu/DejaVuSans-Bold.ttf:"
f"text='{opening_text}':"
"fontcolor=#9CFF00:"
"bordercolor=black:"
"borderw=12:"
"fontsize=92:"
"x=(w-text_w)/2:"
"y=500:"
"enable='between(t,0,3)',"

# LINE 2
"drawtext="
"fontfile=/usr/share/fonts/truetype/"
"dejavu/DejaVuSans-Bold.ttf:"
"text='LINK IN BIO':"
"fontcolor=#FFF500:"
"bordercolor=black:"
"borderw=12:"
"fontsize=120:"
"x=(w-text_w)/2:"
"y=680:"
"enable='between(t,0,3)',"
