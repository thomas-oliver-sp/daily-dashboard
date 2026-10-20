"""Column names taken from the sanitized Salesforce exports.

The closing report is the services-opportunity book. The quote-line report
carries services quotes plus PS that was placed on a license or renewal quote.
"""

OPP_ACCOUNT = "Account Name"
OPP_NAME = "Opportunity Name"
OPP_AMOUNT = "Amount"
OPP_SERVICES_CURRENCY = "Services Value (Net) (converted) Currency"
OPP_SERVICES_VALUE = "Services Value (Net) (converted)"
OPP_WEIGHTED_CURRENCY = "Weighted Revenue (converted) Currency"
OPP_WEIGHTED = "Weighted Revenue (converted)"
OPP_COMMIT = "(old) Commit?"
OPP_PROBABILITY = "Probability (%)"
OPP_STAGE = "Stage"
OPP_FISCAL = "Fiscal Period"
OPP_CLOSE = "Close Date"
OPP_AGE = "Age"
OPP_SERVICES_TYPE = "Services Type"
OPP_STATUS_DATE = "Services Opportunity Status Date"
OPP_STATUS = "Status"
OPP_RECURRING = "Reccurring Services"
OPP_RENEWAL = "Renewal"
OPP_ID = "Opportunity ID"
OPP_PRIMARY = "Primary Quote"
OPP_AGREEMENT = "Agreement Type"
OPP_OWNER = "Opportunity Owner"
OPP_TERRITORY = "Territory"
OPP_BOAT = "Boat"

QUOTE_RECORD_TYPE = "Opportunity Record Type"
QUOTE_ACCOUNT = "Account Name"
QUOTE_NAME = "Opportunity Name"
QUOTE_OWNER = "Opportunity Owner"
QUOTE_GEO = "Geo"
QUOTE_NUMBER = "Primary Quote"
QUOTE_LINE = "Line Name"
QUOTE_PRODUCT = "Product Code"
QUOTE_QTY = "Quantity"
QUOTE_UNIT_CURRENCY = "Net Unit Price (converted) Currency"
QUOTE_UNIT_PRICE = "Net Unit Price (converted)"
QUOTE_DISCOUNT = "Total Discount (%)"
QUOTE_NET_CURRENCY = "Net Total (converted) Currency"
QUOTE_NET = "Net Total (converted)"
QUOTE_FAMILY = "Product Family"
QUOTE_STAGE = "Stage"
QUOTE_CLOSE = "Close Date"
QUOTE_OPP_STATUS = "Opportunity Status"
QUOTE_START = "Effective Start Date"
QUOTE_END = "Effective End Date"
QUOTE_TYPE = "Type"
QUOTE_SERVICES_TERRITORY = "Services Territory"
QUOTE_TERRITORY = "Territory"
QUOTE_OPP_ID = "Opportunity ID"
QUOTE_FISCAL = "Fiscal Period Close"

OPP_REQUIRED = [
    OPP_ACCOUNT,
    OPP_NAME,
    OPP_SERVICES_VALUE,
    OPP_WEIGHTED,
    OPP_PROBABILITY,
    OPP_STAGE,
    OPP_FISCAL,
    OPP_CLOSE,
    OPP_ID,
    OPP_PRIMARY,
    OPP_OWNER,
]

QUOTE_REQUIRED = [
    QUOTE_RECORD_TYPE,
    QUOTE_ACCOUNT,
    QUOTE_NAME,
    QUOTE_OWNER,
    QUOTE_NUMBER,
    QUOTE_LINE,
    QUOTE_PRODUCT,
    QUOTE_NET,
    QUOTE_STAGE,
    QUOTE_CLOSE,
    QUOTE_TERRITORY,
    QUOTE_OPP_ID,
    QUOTE_FISCAL,
]

SERVICES_RECORD_TYPE = "Services"
SHADOW_RECORD_TYPES = ("Direct License", "Renewal")
