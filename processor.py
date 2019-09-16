import sys
import os
import pandas as pd
import re
from datetime import datetime

# currently only supports incal shasta livemon logs

# for now, this script takes in a path filled with BI livemonitor logs, reads
# them all into a structured dataframe (does some unit conversions etc), then
# outputs an xlsx. Once I decide on best data analysis flow, I'll update to do
# more stuff in here, possibly:
# 1. add burn-in board column rather than just Slots
# 2. map directly to ECID of units rather than just slot/DUT combinations
# 3. some default plotting using seaborn or bokeh (maybe include this in burnin
#    report)
# 4. spec limits and "live" alerts (ex., rerun everytime something in some ftp
#    directory gets changed, generate an email showing out of spec stuff)

# The listOfConditions is used to define the multi index of the dataframe, and
# also to detect what's what in the datalog
# the last few of this list of conditions are ones that I made
listOfConditions = ["Slot", "DUT", "Pin", "PS", "ebt",
                    "Measurement Time", "Letter", "Datalog Name",
                    "Line Number"]

# the bools can also be "Undefined" but per Henry this doesn't mean it failed,
# so I don't translate that value
boolTranslator = {
    "OK": 1,
    "Failed": 0,
}


def main():
    filepath = sys.argv[1]

    if not os.path.isdir(filepath):
        print("File path {} does not exist. Exiting...".format(filepath))
        sys.exit()

    totalDF = pd.DataFrame()
    for file in os.listdir(filepath):
        with open(os.path.join(filepath, file)) as fp:
            lineNum = 1
            line = fp.readline()
            while line:
                totalDF = handleLine(
                    line, totalDF, os.path.basename(fp.name), lineNum)
                line = fp.readline()
                lineNum = lineNum + 1
    # pd.MultiIndex.from_frame()
    dfIndex = list(set(listOfConditions) & set(list(totalDF.columns.values)))
    totalDF.set_index(dfIndex, inplace=True, append=True)
    directory = os.path.dirname(fp.name).strip(".").strip("\\")
    dtStr = datetime.now().strftime("%Y%m%dat%H%M%S")
    totalDF.to_excel("livemon_" + directory +
                     "_run" + dtStr + ".xlsx")


def handleLine(line, totalDF, datalogName, lineNum):
    valueDict = {}
    result = [x.strip() for x in line.split(',')]

    # the only things I've seen that are less than 3 fields are either blank
    # lines or multiline notices (which aren't super important), so just ignore
    # this also checks if first line is single character, which should be "E"
    # or "P" (engineering or production)... it's possible the multiline notices
    # can have commas in them, making their array len greater than 3... but
    # they are not predictably formatted, so it causes script to crash, this
    # check fixes that
    if (len(result) > 3 and len(result[0]) == 1):
        # these are parameter: value pairs

        # first collect all the basic info
        valueDict = {
            "Letter": result[0],
            "Measurement Time": datetime.strptime(result[1],
                                                  "%m/%d/%Y %H:%M:%S"),
            # for ebt:
            # just ignore it, it's not consistantly filled out
        }

        # then decide what to do with the rest
        if result[3] == 'Notice':
            valueDict.update({"Notice": result[4]})
        elif result[3] == 'Measure':

            for pairNum in range(4, len(result)):
                pair = [x.strip() for x in result[pairNum].split(': ')]
                if pair[0] in listOfConditions:
                    if pair[0] == "DUT":
                        # if it's DUT then get rid of any spaces, "S" prefix,
                        # "DUT" prefix, and then convert it to string
                        # this is to make the info a little more uniform as well
                        # as remove redundant stuff
                        curVal = pair[1]
                        curVal = curVal.replace(" ", "")
                        curVal = curVal.replace("DUT", "")
                        dutPattern = r"^S(.*)"
                        curVal = re.sub(dutPattern, r"\1", curVal)
                        valueDict.update({pair[0]: curVal})
                    else:
                        valueDict.update({pair[0]: pair[1]})
                elif pair[0] == "Not Used":
                    pass
                else:
                    # to simplify different units, the changes everything to
                    # base unit and then adds to the dict as the condition name
                    # concatanated with the unit in a parenthetical, and the
                    # value as a raw floating point number. Ex., if it's
                    # In.Current = 990 mA
                    # it would input it as
                    # {"In.Current (A)" : "0.99"}
                    numAndUnitPattern = r"(\d+(\.\d*)?) ([a-zA-Z]+)"
                    numAndUnitRE = re.search(numAndUnitPattern, pair[1])
                    if numAndUnitRE:
                        numAndUnit = baseUnit(
                            [numAndUnitRE[1], numAndUnitRE[3]])
                        valueDict.update({
                            pair[0] + " (" + numAndUnit[1] + ")":
                            numAndUnit[0]})
                    else:
                        # passing value is 1, failing value is 0
                        if(pair[1] in boolTranslator):
                            # I swear there has to be a better way to do this..
                            pair[1] = boolTranslator[pair[1]]
                        valueDict.update({pair[0]: pair[1]})
    if valueDict:  # check if there was anything to add

        # if there is then also add in the datalog name and line number
        valueDict.update({
            "Datalog Name": datalogName,
            "Line Number": lineNum
        })
        return totalDF.append(valueDict, ignore_index=True)
    else:
        return totalDF


def baseUnit(numAndUnit):
    numAndUnit[0] = float(numAndUnit[0])
    conversionDict = {
        "M": 1e6,
        "K": 1e3,  # dumb-dumbs at incal capitalize the prefix K
        "k": 1e3,
        "m": 1e-3,
        "u": 1e-6,
        "n": 1e-9
    }
    if(numAndUnit[1][0] in conversionDict):
        numAndUnit[0] = numAndUnit[0]*conversionDict[numAndUnit[1][0]]
        numAndUnit[1] = numAndUnit[1][1:]
    return numAndUnit


if __name__ == '__main__':
    main()
