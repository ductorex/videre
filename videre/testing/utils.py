import os

IMAGE_EXAMPLE = os.path.join(os.path.dirname(__file__), "flowers-7660120_640.jpg")
assert os.path.isfile(IMAGE_EXAMPLE)

LD = {"width": 320, "height": 240}
SD = {"width": 640, "height": 480}
HD = {"width": 1280, "height": 720}
FHD = {"width": 1920, "height": 1080}

# LOREM IPSUM text
# 2024/06/01
# https://fr.wikipedia.org/wiki/Lorem_ipsum
LOREM_IPSUM = (
    "\n"
    "« Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse lectus tortor, dignissim "
    "sit amet, adipiscing nec, ultricies sed, dolor. Cras elementum ultrices diam. Maecenas ligula massa, varius a, "
    "semper congue, euismod non, mi. Proin porttitor, orci nec nonummy molestie, enim est eleifend mi, non fermentum "
    "diam nisl sit amet erat. Duis semper. Duis arcu massa, scelerisque vitae, consequat in, pretium a, enim. "
    "Pellentesque congue. Ut in risus volutpat libero pharetra tempor. Cras vestibulum bibendum augue. Praesent "
    "egestas leo in pede. Praesent blandit odio eu enim. Pellentesque sed dui ut augue blandit sodales. Vestibulum "
    "ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Aliquam nibh. Mauris ac mauris sed "
    "pede pellentesque fermentum. Maecenas adipiscing ante non diam sodales hendrerit.\n"
    "\n"
    "Ut velit mauris, egestas sed, gravida nec, ornare ut, mi. Aenean ut orci vel massa suscipit pulvinar. Nulla "
    "sollicitudin. Fusce varius, ligula non tempus aliquam, nunc turpis ullamcorper nibh, in tempus sapien eros vitae "
    "ligula. Pellentesque rhoncus nunc et augue. Integer id felis. Curabitur aliquet pellentesque diam. Integer quis "
    "metus vitae elit lobortis egestas. Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Morbi vel erat non "
    "mauris convallis vehicula. Nulla et sapien. Integer tortor tellus, aliquam faucibus, convallis id, congue eu, "
    "quam. Mauris ullamcorper felis vitae erat. Proin feugiat, augue non elementum posuere, metus purus iaculis "
    "lectus, et tristique ligula justo vitae magna.\n"
    "\n"
    "Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis, ligula massa adipiscing nisl, "
    "ac euismod nibh nisl eu lectus. Fusce vulputate sem at sapien. Vivamus leo. Aliquam euismod libero eu enim. "
    "Nulla nec felis sed leo placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum augue. "
    "Nulla tincidunt tincidunt mi. Curabitur iaculis, lorem vel rhoncus faucibus, felis magna fermentum augue, et "
    "ultricies lacus lorem varius purus. Curabitur eu amet. »\n"
).strip()

TEXT_SAMPLES = {
    "french_lr_arabic_rl": (
        "L'Empire ottoman (en turc ottoman : دولت عليه عثمانیه / devlet-i ʿaliyye-i ʿos̲mâniyye, littéralement "
        "« l'État ottoman exalté » ; en turc : Osmanlı İmparatorluğu ou Osmanlı Devleti[a]), connu historiquement en "
        "Europe de l'Ouest comme l'Empire turc, la Turquie, ou bien la Turquie ottomane, est un empire fondé à la fin "
        "du XIIIe siècle au nord-ouest de l'Anatolie, dans la commune de Söğüt (actuelle province de Bilecik), par "
        "le chef tribal oghouze Osman Ier, fondateur de la dynastie ottomane (ottoman vient de l'arabe ʿuṯmānī عُثْمَانِي, "
        "dérivé de ʿuṯmān عُثْمَان, nom arabisé d'Osman et vient également de Ataman, nom turcisé d’Osman)."
    ),
    "french_japanese": (
        "Oda Nobunaga (織田 信長?, né le 23 juin 1534 et mort le 21 juin 1582) "
        "était un daimyō important de la période Sengoku de l'histoire du Japon."
    ),
    "japanese": (
        "織田 信長（おだ のぶなが）は、日本の戦国時代から安土桃山時代にかけての武将・大名。戦国の三英傑の一人。\n\n尾張国（現在の愛知県）出身。"
        "織田信秀の嫡男。家督争いの混乱を収めた後、桶狭間の戦いで今川義元を討ち取り、勢力を拡大した。足利義昭を奉じて上洛し、後には足利義昭を追放"
        "することで、畿内を中心に独自の中央政権（「織田政権」[注釈 5]）を確立して天下人となった。しかし、天正10年6月2日（1582年6月21日）、家"
        "臣・明智光秀に謀反を起こされ、本能寺で自害した。"
    ),
    "chinese": (
        "孔子在世時被譽為“天縱之聖”、“天之木鐸”，西漢時由董仲舒倡議，汉武帝施行“獨尊儒術”政策，后世统治者或孔教信徒陆续尊稱孔子為聖人、文聖、"
        "至聖[註 4]、至聖先師、大成至聖先師[註 5]、万世师表[註 6]。道教称号：太極上真九疑主宰文昌皇人玄聖道君、東海廣桑山真君、闡猷大帝、"
        "興儒盛世天尊[6]。在朝廷影響之下，孔子在民間地位亦愈加崇高，最後被神格化，為智慧之神。"
    ),
    "chinese_simplified": (
        "孔丘（前551年9月28日—前479年4月11日），字仲尼，鲁国陬邑（今山东省曲阜市）人，祖籍宋国栗邑（今河南省夏邑县），中国古代思想家、"
        "教育家、政治家，儒家学派创始人，“至圣先师”。孔子开创私人讲学之风，倡导仁、义、礼、智、信。孔子曾带领弟子周游列国十四年，晚年修订"
        "《诗》《书》《礼》《乐》《易》《春秋》六经。"
    ),
    # All these following lines_* cases should produce the exact same rendering
    "lines_linux": "L1\nL2\n\nL4\n\n\n\nl8",  # each \n => new line
    "lines_mac": "L1\rL2\r\rL4\r\r\r\rl8",  # each \r => new line
    "lines_windows": "L1\r\nL2\r\n\r\nL4\r\n\r\n\r\n\r\nl8",  # each \r\n => new line
    "lines_malformed": "L1\nL2\n\rL4\r\n\n\n\nl8",  # \r\n => new line, then remaining \r => new line, or \n => new line
    "arabic": """
أودا نوبوناغا (織田 信長؟، [o.da (|) no.bɯ(ꜜ).na.ɡa, -na.ŋa] ⓘ; 23 يونيو 1534 – 21 يونيو 1582) هو قائد ياباني ومن أكبر الجنرلات الذين عرفهم تاريخ البلاد. كان أول الثلاثة الذين ساهموا في توحيد اليابان بعد فترة الانقسامات.
النشأة والصعود

ولد «نوبوناغا» سنة 1534 في قلعة ناغويا في مقاطعة أواري، ورث ولما يبلغ الـ17 من العمر بعد الحكم عن والده الذي كان سيدا على منطقة أواري، كانت تركة أبيه له تتمثل في القلعة والأراضي المحيطة بها. انطلاقا من أراضي عشيرته (عشيرة أودا) المتواضعة في منطقة أو-واري(尾張) وعلى امتداد الـ31 سنة المقبلة ارتقى نوبونوغاوتوسع شيئا فشيئا ثم هزم منافسيه من العشائر الأخرى، رغم تفوقهم في العدة والعدد حتى دانت له بلاد اليابان بأكملها.
""".strip(),
    # Modern Hebrew without nikkud, then a verse with nikkud (Genesis 1:1) to test stacked combining marks
    "hebrew": (
        "ירושלים היא בירת מדינת ישראל והעיר הגדולה ביותר בה, הן בגודל האוכלוסייה והן בשטחה. נכונותה של ירושלים כבירה "
        "אינה מוכרת על ידי רוב מדינות העולם.\n\n"
        "בעברית מודרנית הניקוד אינו נדרש בכתיבה רגילה: בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ."
    ),
    # Devanagari: tests vowel reordering (ि is stored after the consonant but rendered before it)
    # and consonant clusters with halant (्) and nukta (़).
    "devanagari": (
        "हिन्दी भारत में सबसे अधिक बोली और समझी जाने वाली भाषा है। हिन्दी भारत की राजभाषा है। "
        "केन्द्रीय स्तर पर भारत में दूसरी आधिकारिक भाषा अंग्रेज़ी है। नमस्ते।"
    ),
    # Thai: no spaces between words, requires UAX#14 line breaking. Also tests leading vowels (เ, ไ)
    # which are stored after but rendered before their consonant.
    "thai": (
        "ภาษาไทยเป็นภาษาทางการของประเทศไทย และเป็นภาษาแม่ของชาวไทย "
        "ภาษาไทยจัดอยู่ในตระกูลภาษาขร้า-ไท เป็นภาษาคำโดดที่มีระบบเสียงวรรณยุกต์"
    ),
    # Emoji: simple SMP codepoints, ZWJ family sequence, regional indicator flags, skin tone modifiers
    "emoji": "Hello 👋 World 🌍! Family: 👨‍👩‍👧‍👦 Flags: 🇫🇷🇯🇵🇸🇦 Skin tones: 👍🏽👍🏿 Faces: 😀🥰🤔😂",
    "latin_ligatures": "Laetitia, coeur, oesophage. Lætitia, cœur, œsophage (fi fl ff ffi ffl) (ﬁ ﬂ ﬀ ﬃ ﬄ)",
}
