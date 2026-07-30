import re

def allergen_regex(allergen_list: list[str]) -> re.Pattern:
	patterns = []

	# Sort longest-first so "peanut butter" matches before "peanut"
	for term in sorted(allergen_list, key=len, reverse=True):
		escaped_term = re.escape(term)

		# Allow for matching plural combinations (i.e. "peanut" / "peanuts").
		patterns.append(rf"\b{escaped_term}\b" if term.endswith("s") else rf"\b{escaped_term}s?\b")

	combined_pattern = "|".join(patterns)

	return re.compile(combined_pattern, re.IGNORECASE)

UK_14 = allergen_regex([
	# Celery
	"celery", "celeriac",

	# Cereals containing gluten
	"cereals containing gluten", "gluten", "wheat", "rye", "barley", "oats", "spelt", "khorasan", "kamut", "triticale",
	"farro", "freekeh", "bulgur", "semolina", "couscous", "einkorn", "emmer",

	# Crustaceans
	"crustacean", "prawn", "shrimp", "crab", "lobster", "crayfish", "langoustine", "scampi",

	# Eggs
	"eggs", "egg", "egg yolk", "egg white", "albumin",

	# Fish
	"fish", "fishes", "anchovy", "anchovies", "isinglass", "tuna", "salmon", "cod", "haddock"

	# Lupin
	"lupin", "lupines", "lupine",

	# Milk / Dairy
	"milk", "butter", "cream", "cheese", "whey", "ghee", "casein", "caseinate", "lactalbumin", "lactoglobulin",
	"lactose", "curd", "curds", "yoghurt", "yogurt",

	# Molluscs
	"molluscs", "mollusc", "mollusk", "mollusks", "mussel", "oyster", "squid", "calamari",
	"snail", "escargot", "clam", "scallop", "octopus", "cuttlefish", "cockles", "whelks",

	# Mustard
	"mustard",

	# Tree Nuts
	"nut", "almond", "hazelnut", "walnut", "cashew", "pecans", "pecan", "pistachio", "macadamia", "marzipan",
	"praline",

	# Peanuts
	"peanut", "groundnut", "peanut butter",

	# Sesame
	"sesame", "tahini",

	# Soy / Soya
	"soy", "soya", "soybean", "edamame", "tofu", "tempeh",

	# Sulphur dioxide / Sulphites
	"sulphur dioxide", "sulfur dioxide", "sulphite", "sulfite", "e220", "e221", "e222", "e223", "e224", "e225", "e226",
	"e227", "e228"
])
