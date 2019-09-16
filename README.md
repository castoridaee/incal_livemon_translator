# incal_livemon_translator
Translates Incal live monitor files into more usable format. Currently it only handles Incal Shasta files. Input is a directory containing multiple .log files and output is an .xlsx. Once I decide on best data analysis flow, I'll update to do more stuff, possibly:
1. add burn-in board column rather than just Slots
2. map directly to ID of units rather than just slot/DUT combinations
3. some default plotting using seaborn or bokeh
4. spec limits and "live" alerts (ex., rerun everytime something in some ftp directory gets changed, generate an email showing out of spec stuff)
