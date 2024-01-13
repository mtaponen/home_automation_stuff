# Simple porssisahko service in python flask

Not production quality - runs Flask which is not for heavy use.
Expecting only few requests / hour so may not be an issue
Still issues with timezone handling as input data is somehow wonky
and maybe my handling is incorrect as well

Depends on api.porssisahko.net for getting the price-info

implements 3 endpoints
- GET (sic!)/Update price info (this is automatically called on startup & scheduled)
- GET lowest average of 3 consecutive hours (cheapest period)
- GET current price
