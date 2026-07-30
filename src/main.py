from datetime import date, datetime, timedelta
from gooey import Gooey, GooeyParser
from json import dump, load
from label import Label, preview_label, print_label

ui_date_format = "%Y-%m-%d"
default_expiry_date = (date.today() + timedelta(days=2))

def add_create_page(command):
	product_details = command.add_argument_group("Product Details", gooey_options={
		"columns": 2
	})

	product_details.add_argument("--Name",
		type=str,
		default="",
		help="Product Name (e.g., Ham Sandwich).",
	)
	
	product_details.add_argument("--Description",
		type=str,
		default="",
		help="Short product description.",
	)
	
	product_details.add_argument("--Ingredients",
		type=str,
		default="",
		metavar="Ingredient List",
		help="Comma separated list of ingredients (e.g. Bread containing gluten, butter, ham).",
	)
	
	product_details.add_argument("--Price",
		type=int,
		default=0,
		metavar="Price",
		help="Listed item price in pence.",
	)

	output_file = command.add_argument_group("Output File")

	output_file.add_argument("Path",
		type=str,
		widget="FileSaver",
		help="Choose where the label file will be saved to.",
		gooey_options={"wildcard": "JSON Files (*.json)|*.json"}
	)

def add_print_page(command):
	input_file = command.add_argument_group("Input File")

	input_file.add_argument("Path", 
		type=str,
		widget="FileChooser",
		help="Select the label file to print.",
		gooey_options={"wildcard": "JSON Files (*.json)|*.json"}
	)

	input_file.add_argument("--Expiry",
		widget="DateChooser",
		default=default_expiry_date.strftime(ui_date_format),
		metavar="Use-By Date",
		help="Date by which the product must be used.",
	)

	printing = command.add_argument_group("Printing")
	print_mode = printing.add_mutually_exclusive_group()

	print_mode.add_argument("--Preview",
		action="store_true",
		metavar="Preview-Only",
		help="Preview the label without printing it.",
	)

	print_mode.add_argument("--Copies",
		type=int,
		default=1,
		widget="IntegerField",
		metavar="Print Copies",
		help="Print this many labels.",
	)

@Gooey(program_name="Clear Plate", return_to_config=True, default_size=(600, 750), navigation="TABBED", required_cols=1, optional_cols=1)
def main():
	parser = GooeyParser(
		description="Natasha's Law-Compliant Label Generator for Brother QL-700",
	)

	sub_parsers = parser.add_subparsers(help="Actions", dest="Action")

	add_create_page(sub_parsers.add_parser("Create"))
	add_print_page(sub_parsers.add_parser("Print"))

	args = parser.parse_args()

	match args.Action:
		case "Create":
			if not args.Path.endswith(".json"):
				args.Path += ".json"

			if not args.Description.endswith("."):
				args.Description += "."

			with open(args.Path, "w", encoding="utf-8") as file:
				product = {
					"name": args.Name.title(),
					"description": args.Description.title(),
					"ingredients": [i.strip().title() for i in args.Ingredients.split(",") if i.strip()],
					"price": args.Price,
				}

				dump(product, file, indent=4)

		case "Print":
			with open(args.Path, "r", encoding="utf-8") as file:
				product = load(file)

				label = Label(
					name=product["name"],
					description=product["description"],
					ingredients=set(product["ingredients"]),
					price=product["price"],
					expiry=datetime.strptime(args.Expiry, ui_date_format),
				)

				label_image = label.to_image()

				if args.Preview:
					preview_label(label_image)

				else:
					print_label(label_image, copies=args.Copies)

if __name__ == "__main__":
	main()
