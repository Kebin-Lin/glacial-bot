#include <iostream>
#include <string>
#include <math.h>
#include <time.h>
#include <vector>
#include <algorithm>

enum EnhanceStates {SUCCESS, MAINTAIN, DECREASE, DESTROY};

const double CHANCES[22][4] = { //x -> x+1
    {.95, .05, 0, 0}, //0
    {.9, .1, 0, 0}, //1
    {.85, .15, 0, 0}, //2
    {.85, .15, 0, 0}, //3
    {.8, .2, 0, 0}, //4
    {.75, .25, 0, 0}, //5
    {.7, .3, 0, 0}, //6
    {.65, .35, 0, 0}, //7
    {.6, .4, 0, 0}, //8
    {.55, .45, 0, 0}, //9
    {.5, .5, 0, 0}, //10
    {.45, 0, .55, 0}, //11
    {.4, 0, .594, .006}, //12
    {.35, 0, .637, .013}, //13
    {.3, 0, .686, .014}, //14
    {.3, .679, 0, .021}, //15
    {.3, 0, .679, .021}, //16
    {.3, 0, .679, .021}, //17
    {.3, 0, .672, .028}, //18
    {.3, 0, .672, .028}, //19
    {.3, .63, 0, .07}, //20
    {.3, 0, .63, .07} //21
};

const double CHANCES_STARCATCH[22][4] = {
    {0.99275, 0.00725, 0.0, 0.0},
    {0.9405, 0.0595, 0.0, 0.0},
    {0.88825, 0.11175, 0.0, 0.0},
    {0.88825, 0.11175, 0.0, 0.0},
    {0.836, 0.164, 0.0, 0.0},
    {0.78375, 0.21625, 0.0, 0.0},
    {0.7315, 0.2685, 0.0, 0.0},
    {0.67925, 0.32075, 0.0, 0.0},
    {0.627, 0.373, 0.0, 0.0},
    {0.57475, 0.42525, 0.0, 0.0},
    {0.5225, 0.4775, 0.0, 0.0},
    {0.47025, 0.0, 0.52975, 0.0},
    {0.418, 0.0, 0.57618, 0.00582},
    {0.36575, 0.0, 0.621565, 0.012685},
    {0.3135, 0.0, 0.67277, 0.01373},
    {0.3135, 0.665905, 0.0, 0.020595},
    {0.3135, 0.0, 0.665905, 0.020595},
    {0.3135, 0.0, 0.665905, 0.020595},
    {0.3135, 0.0, 0.65904, 0.02746},
    {0.3135, 0.0, 0.65904, 0.02746},
    {0.3135, 0.61785, 0.0, 0.06865},
    {0.3135, 0.0, 0.61785, 0.06865}
};

const double hundredPerc[4] = {1, 0, 0, 0};

int roundHund(double n) {
    return (int) ((int) n % 100 >= 50 ? ((int) n + 100) / 100 * 100 : (int) n / 100 * 100);
}

int costFormula(int currStar, int equiplv) {
    int lvcubed = equiplv * equiplv * equiplv;
    if (currStar < 10) {
        return roundHund(1000 + lvcubed * (currStar + 1) / 25.);
    } else if (currStar < 15) {
        return roundHund(1000 + lvcubed * std::pow((currStar + 1), 2.7) / 400);
    } else if (currStar < 18) {
        return roundHund(1000 + lvcubed * std::pow((currStar + 1), 2.7) / 120);
    } else if (currStar < 20) {
        return roundHund(1000 + lvcubed * std::pow((currStar + 1), 2.7) / 110);
    } else if (currStar < 25) {
        return roundHund(1000 + lvcubed * std::pow((currStar + 1), 2.7) / 100);
    }
}

void trial(int start, int goal, int equiplv, bool safeguard, bool fivetenfifteen, bool thirtyperc, bool plustwo, const double (&chances)[22][4], long& totalCost, int& totalBooms, int* savedCosts) {
    int currStar = start;
    long mesos = 0;
    int numConsecFails = 0;
    int booms = 0;
    while (currStar != goal) {
        bool safeguardApplicable = safeguard && currStar >= 12 && currStar <= 16;
        // std::cout << safeguardApplicable << std::endl;
        int baseCost;
        if (savedCosts[currStar] == 0) {
            savedCosts[currStar] = costFormula(currStar, equiplv);
        }
        baseCost = savedCosts[currStar];
        int currCost = thirtyperc ? roundHund(baseCost * .7) : baseCost;
        const double *rates;
        if (numConsecFails > 1 || (fivetenfifteen && (currStar == 5 || currStar == 10 || currStar == 15))) { //Chance time or 5/10/15
            rates = &hundredPerc[0];
        } else {
            rates = &chances[currStar][0];
        }
        // for (int i = 0; i < 4; i++) {
        //     std::cout << rates[i] << ' ';
        // }
        // std::cout << std::endl;

        if (rates[0] != 1 and safeguardApplicable) {
            currCost += baseCost;
        }
        mesos += currCost;
        double randNum = std::rand() / (RAND_MAX + 1.);
        double accum = 0;
        int mode = -1;
        do { //Check for enhancement state
            mode++;
            accum += rates[mode];
        }
        while (randNum > accum);
        // std::cout << mode << std::endl;
        switch (mode) {
            case SUCCESS:
                if (plustwo) {
                    if (currStar <= 10) {
                        currStar++;
                    }
                }
                currStar++;
                break;
            case MAINTAIN:
                break;
            case DECREASE:
                currStar--;
                break;
            case DESTROY:
                if (safeguardApplicable) {
                    if (currStar % 5 != 0) {
                        currStar--;
                    }
                } else {
                    booms++;
                    currStar = 12;
                }
                break;
        }
        //Chance time handling
        if (mode == DECREASE) {
            numConsecFails++;
        } else {
            numConsecFails = 0;
        }
    }
    totalCost += mesos;
    totalBooms += booms;
}

void runTrials(int start, int goal, int equiplv, int numTrials, double discount, bool safeguard, bool fivetenfifteen, bool thirtyperc, bool starcatch, bool plustwo,
               long& avgCost, double& avgBooms, double& noBoomRate, std::vector<long>& mesoPercentiles, std::vector<int>& boomPercentiles) {
    long totalCost = 0;
    int totalBooms = 0;
    int numNoBooms = 0;
    int savedCosts[22] = {0};
    std::vector<long> mesoVector;
    std::vector<int> boomVector;
    mesoVector.reserve(numTrials);
    boomVector.reserve(numTrials);
    for (int i = 0; i < numTrials; i++) {
        long mesoCost = 0;
        int numBooms = 0;
        trial(start, goal, equiplv, safeguard, fivetenfifteen, thirtyperc, plustwo, starcatch ? CHANCES_STARCATCH : CHANCES, mesoCost, numBooms, &savedCosts[0]);
        mesoVector.push_back(mesoCost);
        boomVector.push_back(numBooms);
        totalCost += mesoCost;
        totalBooms += numBooms;
        if (numBooms == 0) {
            numNoBooms++;
        }
    }
    std::sort(mesoVector.begin(), mesoVector.end());
    std::sort(boomVector.begin(), boomVector.end());
    mesoPercentiles = {mesoVector[(int) (numTrials * .75)], mesoVector[(int) (numTrials * .85)], mesoVector[(int) (numTrials * .95)]};
    boomPercentiles = {boomVector[(int) (numTrials * .75)], boomVector[(int) (numTrials * .85)], boomVector[(int) (numTrials * .95)]};
    avgCost = totalCost / numTrials * discount;
    avgBooms = ((double) totalBooms) / numTrials;
    noBoomRate = ((double) numNoBooms) / numTrials;
}

int main(int argc, char *argv[]) {
    std::srand(time(NULL));

    if (argc < 9) {
        std::cout << "Error" << std::endl << "Error" << std::endl << "Error" << std::endl;
    } else {
        long avgCost;
        double avgBooms;
        double noBoomRate;
        std::vector<long> mesoPercentiles;
        std::vector<int> boomPercentiles;
        runTrials(std::stoi(argv[1]), std::stoi(argv[2]), std::stoi(argv[3]), std::stoi(argv[4]), std::stod(argv[5]),
                  std::stoi(argv[6]), std::stoi(argv[7]), std::stoi(argv[8]), std::stoi(argv[9]), std::stoi(argv[10]),
                  avgCost, avgBooms, noBoomRate, mesoPercentiles, boomPercentiles);
        std::cout << avgCost << std::endl << avgBooms << std::endl << noBoomRate << std::endl;
        for(int i = 0; i < mesoPercentiles.size(); i++) {
            std::cout << mesoPercentiles[i] << " ";
        }
        std::cout << std::endl;
        for(int i = 0; i < boomPercentiles.size(); i++) {
            std::cout << boomPercentiles[i] << " ";
        }
        std::cout << std::endl;
    }
}