#include <iostream>
#include <string>
#include <math.h>
#include <time.h>
#include <vector>
#include <algorithm>

enum FlameLines {
    STR, DEX, INT, LUK, STRDEX, STRINT, STRLUK, DEXINT, DEXLUK, INTLUK, DEF, HP, MP, ALL, EQUIPLV, //Universal
    ATT, MATT, SPEED, JUMP, //Non Weapon
    W_ATT, W_MATT, BOSS, DMG //Weapon Only
};

const double P_TIER_RATES[5] = {.2, .3, .36, .14, 0};
const double R_TIER_RATES[5] = {0, .29, .45, .25, .01};
const double STAT_TIER_VALS[14][7] = {
    {1, 2, 3, 4, 5, 6, 7}, //0-19
    {2, 4, 6, 8, 10, 12, 14}, //20-39
    {3, 6, 9, 12, 15, 18, 21}, //40-59
    {4, 8, 12, 16, 20, 24, 28}, //60-79
    {5, 10, 15, 20, 25, 30, 35}, //80-99
    {6, 12, 18, 24, 30, 36, 42}, //100-119
    {7, 14, 21, 28, 35, 42, 49}, //120-139
    {8, 16, 24, 32, 40, 48, 56}, //140-159
    {9, 18, 27, 36, 45, 54, 63}, //160-179
    {10, 20, 30, 40, 50, 60, 70}, //180-199
    {11, 22, 33, 44, 55, 66, 77}, //200-219
    {12, 24, 36, 48, 60, 72, 84}, //220-239
    {13, 26, 39, 52, 65, 78, 91}, //240-259
    {14, 28, 42, 56, 70, 84, 98} //260-275
};

const int USAGE_LIMIT = 100000;

void useFlame(int lvbracket, bool flameAdvantage, int& statOutput, int& statPercOutput, int& dmgOutput, int& attOutput, const double (&tierRates)[5], std::vector<FlameLines>& possibleLines) {
    int numLines = flameAdvantage ? 4 : std::rand() % 4 + 1;
    std::vector<FlameLines> selectedLines;
    for (int i = 0; i < numLines; i++) { //Select random lines with no repeating lines
        int selectedIndex = std::rand() % (possibleLines.size());
        selectedLines.push_back(possibleLines[selectedIndex]);
        possibleLines[selectedIndex] = possibleLines[possibleLines.size() - 1];
        possibleLines.pop_back();
    }
    for (int i = 0; i < numLines; i++) {
        possibleLines.push_back(selectedLines[i]); //Repair possibility vector
        double randNum = std::rand() / (RAND_MAX + 1.);
        double accum = 0;
        int tier = -1;
        do { //Check for enhancement state
            tier++;
            accum += tierRates[tier];
        }
        while (randNum > accum);
        if (flameAdvantage) {
            tier += 2;
        }
        switch (selectedLines[i]) {
            case STR:
                statOutput += STAT_TIER_VALS[lvbracket][tier];
                break;
            case STRDEX: case STRINT: case STRLUK:
                statOutput += STAT_TIER_VALS[lvbracket / 2 * 2 + 1][tier] / 2;
                break;
            case ATT: case W_ATT:
                attOutput = tier + 1;
                break;
            case ALL:
                statPercOutput = tier + 1;
                break;
            case BOSS:
                dmgOutput += (tier + 1) * 2;
                break;
            case DMG:
                dmgOutput += tier + 1;
                break;
            default:
                break;
        }
    }
    // std::cout << statOutput << std::endl;
}

int trial(int lvbracket, bool flameAdvantage, int targetScore, int targetDmg, int targetAttTier, const double (&tierRates)[5], std::vector<FlameLines>& possibleLines) {
    int flamesConsumed = 0;
    while (flamesConsumed < USAGE_LIMIT) {
        flamesConsumed++;
        int rolledStat, rolledStatPerc, rolledDmg, rolledAtt;
        rolledStat = rolledStatPerc = rolledDmg = rolledAtt = 0;
        useFlame(lvbracket, flameAdvantage, rolledStat, rolledStatPerc, rolledDmg, rolledAtt, tierRates, possibleLines);
        int flameScore = rolledStat + (rolledStatPerc * 8);
        if (targetAttTier == -1) {
            flameScore += rolledAtt * 3;
        }
        if (flameScore >= targetScore && rolledDmg >= targetDmg && rolledAtt >= targetAttTier) {
            break;
        }
    }
    return flamesConsumed;
}

void runTrials(int equiplv, bool flameAdvantage, int targetScore, int targetDmg, int targetAttTier, int numTrials, bool useRainbow, double& avgUsage, std::vector<int>& usagePercentiles) {
    std::vector<int> usageVector;
    std::vector<FlameLines> possibleLines = {STR, DEX, INT, LUK, STRDEX, STRINT, STRLUK, DEXINT, DEXLUK, INTLUK, DEF, HP, MP, ALL, EQUIPLV};
    if (targetDmg == -1) { //Non Weapon
        possibleLines.insert(possibleLines.end(), {ATT, MATT, SPEED, JUMP});
    } else { //Weapon
        possibleLines.insert(possibleLines.end(), {W_ATT, W_MATT, BOSS, DMG});
    }
    int totalFlamesConsumed = 0;
    int lvbracket = equiplv / 20;
    for (int i = 0; i < numTrials; i++) {
        int trialResult = trial(lvbracket, flameAdvantage, targetScore, targetDmg, targetAttTier, useRainbow ? R_TIER_RATES : P_TIER_RATES, possibleLines);
        if (trialResult == USAGE_LIMIT) {
            usagePercentiles = {-1, -1, -1};
            avgUsage = -1;
            return;
        }
        usageVector.push_back(trialResult);
        totalFlamesConsumed += trialResult;
    }
    std::sort(usageVector.begin(), usageVector.end());
    usagePercentiles = {usageVector[(int) (numTrials * .75)], usageVector[(int) (numTrials * .85)], usageVector[(int) (numTrials * .95)]};
    avgUsage = ((double) totalFlamesConsumed) / numTrials;
}

int main(int argc, char *argv[]) {
    std::srand(time(NULL));
    if (argc < 8) {
        std::cout << "Error" << std::endl << "Error" << std::endl << "Error" << std::endl;
    } else {
        double avgUsage;
        std::vector<int> usagePercentiles;
        runTrials(std::stoi(argv[1]), std::stoi(argv[2]), std::stoi(argv[3]), std::stoi(argv[4]), std::stoi(argv[5]),
                  std::stoi(argv[6]), std::stoi(argv[7]), avgUsage, usagePercentiles);
        std::cout << avgUsage << std::endl;
        for(int i = 0; i < usagePercentiles.size(); i++) {
            std::cout << usagePercentiles[i] << " ";
        }
        std::cout << std::endl;
    }
}