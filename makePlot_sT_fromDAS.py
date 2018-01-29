#!/usr/bin/env python

from __future__ import print_function, division

import os, sys, ROOT, argparse, array
import numpy as np
from tmProgressBar import tmProgressBar

inputArgumentsParser = argparse.ArgumentParser(description='Run STEALTH selection.')
inputArgumentsParser.add_argument('--inputFilePath', required=True, help='Path to input file.',type=str)
inputArgumentsParser.add_argument('--n_sTBins', default=8, help='Number of sT bins.',type=int)
inputArgumentsParser.add_argument('--sTMin', default=800., help='Min value of sT.',type=float)
inputArgumentsParser.add_argument('--sTMax', default=1600., help='Max value of sT.',type=float)
inputArgumentsParser.add_argument('--sTNormRangeMin', default=800., help='Min value of sT for normalization.',type=float)
inputArgumentsParser.add_argument('--sTNormRangeMax', default=1600., help='Max value of sT for normalization.',type=float)
inputArgumentsParser.add_argument('--nJetsMax', default=6, help='Max number of jets.',type=int)
inputArgumentsParser.add_argument('--nJetsNorm', default=2, help='Number of jets w.r.t. which to normalize the sT distributions for other jets.',type=int)
inputArgumentsParser.add_argument('--outputFilesSuffix', required=True, help='Prefix for output files.',type=str)
inputArguments = inputArgumentsParser.parse_args()

rooVar_sT = ROOT.RooRealVar("rooVar_sT", "rooVar_sT", inputArguments.sTMin, inputArguments.sTMax)
# rooVar_decayParameter = ROOT.RooRealVar("rooVar_decayParameter", "rooVar_decayParameter", 4.67)
# rooVar_logTermCoefficient = ROOT.RooRealVar("rooVar_logTermCoefficient", "rooVar_logTermCoefficient", 0.9)
# rooVar_expCoefficient = ROOT.RooRealVar("rooVar_expCoefficient", "rooVar_expCoefficient", 5.0)

sTBackgroundFunctionNames = ["inversePowerLaw", "logModulatedInversePowerLaw", "inverseExponential"]
# sTBackgroundFunctionDefinitions = {
#     "inversePowerLaw": "1.0/pow(rooVar_sT,rooVar_decayParameter)",
#     "logModulatedInversePowerLaw": "1.0/pow(rooVar_sT/13000.,rooVar_logTermCoefficient*log(rooVar_sT))",
#     "inverseExponential": "1.0/exp(rooVar_expCoefficient*rooVar_sT/13000.)"
# }
# sTBackgroundFunctionDependencies = {
#     "inversePowerLaw": ROOT.RooArgList(rooVar_sT, rooVar_decayParameter),
#     "logModulatedInversePowerLaw": ROOT.RooArgList(rooVar_sT, rooVar_logTermCoefficient),
#     "inverseExponential": ROOT.RooArgList(rooVar_sT, rooVar_expCoefficient)
# }
# rooPDFs = {}
# for sTBackgroundFunctionName in sTBackgroundFunctionNames:
#     rooPDFs[sTBackgroundFunctionName] = ROOT.RooGenericPdf("{name}PDF".format(name=sTBackgroundFunctionName), "{name}PDF".format(name=sTBackgroundFunctionName), sTBackgroundFunctionDefinitions[sTBackgroundFunctionName], sTBackgroundFunctionDependencies[sTBackgroundFunctionName])
sTBackgroundLineColors = {
    "inversePowerLaw": ROOT.kBlue,
    "logModulatedInversePowerLaw": ROOT.kBlack,
    "inverseExponential": ROOT.kRed
}
sTBackgroundLabels = {
    "inversePowerLaw": "1/S_{T}^{p_{0}}",
    "logModulatedInversePowerLaw": "1/S_{T}^{p_{1}lnS_{t}}",
    "inverseExponential": "1/e^{p_{2}S_{T}}"
}

def make_ratio_graph(g_name, h_num, h_den):
    gae = ROOT.TGraphAsymmErrors()
    gae.SetName(g_name)
    h_rat = h_num.Clone()
    h_rat.Divide(h_den)
    for i in range(1, h_rat.GetNbinsX() + 1):
        n_rat = 0
        r_high = 0

        # tail = (1 - cl) / 2; for 95% CL, tail = (1 - 0.95) / 2 = 0.025
        tail = 0.16
        if h_num.GetBinError(i) == 0.0 or h_den.GetBinError(i) == 0.0:
            continue

        n_num = pow(h_num.GetBinContent(i) / h_num.GetBinError(i), 2)
        n_den = pow(h_den.GetBinContent(i) / h_den.GetBinError(i), 2)
        q_low = ROOT.Math.fdistribution_quantile_c(1 - tail, n_num * 2, (n_den + 1) * 2)
        r_low = q_low * n_num / (n_den + 1)
        if n_den > 0:
            n_rat = n_num / n_den
            q_high = ROOT.Math.fdistribution_quantile_c(tail, (n_num + 1) * 2, n_den * 2)
            r_high = q_high * (n_num + 1) / n_den
            gae.SetPoint(i-1,
                h_rat.GetBinCenter(i),
                h_rat.GetBinContent(i)
            )
            gae.SetPointError(i-1,
                h_rat.GetBinWidth(i) / 2,
                h_rat.GetBinWidth(i) / 2,
                n_rat - r_low,
                r_high - n_rat
            )
        # print ("i = " + str(i) + ": point = (" + str(h_rat.GetBinCenter(i)) + "," + str(h_rat.GetBinContent(i)) + "), point errors = (" + str(h_rat.GetBinWidth(i) / 2) + "," + str(h_rat.GetBinWidth(i) / 2) + "," + str(n_rat - r_low) + "," + str(r_high - n_rat) + ")")
    gae.GetXaxis().SetRangeUser(
        h_rat.GetBinLowEdge(1),
        h_rat.GetBinLowEdge(h_rat.GetNbinsX()) +
        h_rat.GetBinWidth(h_rat.GetNbinsX()))
    return gae

def getRatioChiSq(binContents, binErrors):
    ratioChiSq = 0.
    for binCounter in range(len(binContents)):
        binContent = binContents[binCounter]
        binError = binErrors[binCounter]
        if (binError > 0. and binContent > 0.):
            ratioChiSq += pow(binContent-1, 2)/pow(binError, 2)
    return ratioChiSq

sw = ROOT.TStopwatch()
sw.Start()

chain_in = ROOT.TChain('ggNtuplizer/EventTree')
chain_in.Add(inputArguments.inputFilePath)
n_entries = chain_in.GetEntries()
print ('Total number of events: ' + str(n_entries))

# Initialize histograms and ttrees
n_sT_bins = inputArguments.n_sTBins
sT_min = inputArguments.sTMin
sT_max = inputArguments.sTMax
n_jets_min = 2
n_jets_max = inputArguments.nJetsMax
file_out = ROOT.TFile('analysis/h_sTs_{outputFilesSuffix}.root'.format(outputFilesSuffix=inputArguments.outputFilesSuffix), 'recreate')
histograms = {}
for i in range(n_jets_min, n_jets_max + 1):
    hist_name = 'sT_' + str(i) + 'Jets'
    histograms[hist_name] = ROOT.TH1F(
        'h_' + hist_name, ';S_{T} (GeV);AU', n_sT_bins, sT_min, sT_max
        )
    histograms[hist_name].Sumw2()

normTree = ROOT.TTree("normTree", "normTree")
# norm_sTArray = np.zeros(1, dtype=float)
norm_sTArray = array.array('f', [0.])
normTree.Branch('rooVar_sT', norm_sTArray, 'rooVar_sT/F')

# Fill histograms
progressBar = tmProgressBar(n_entries)
progressBarUpdatePeriod = n_entries//1000
progressBar.initializeTimer()
for j_entry in range(n_entries):
    i_entry = chain_in.LoadTree(j_entry)
    if i_entry < 0:
        break
    nb = chain_in.GetEntry(j_entry)
    if nb <= 0:
        continue

    if (j_entry%progressBarUpdatePeriod == 0): progressBar.updateBar(1.0*j_entry/n_entries, j_entry)

    n_stealth_jets = chain_in.b_nJets
    sT = chain_in.b_evtST
    if (n_stealth_jets == inputArguments.nJetsNorm and (sT > sT_min and sT < sT_max)):
        # print("Storing sT = " + str(sT))
        norm_sTArray[0] = sT
        normTree.Fill()
    i = n_stealth_jets
    if (i > n_jets_max): i = n_jets_max
    # trees[i].Fill()
    if n_stealth_jets >= n_jets_min and n_stealth_jets <= n_jets_max:
        histograms['sT_' + str(n_stealth_jets) + 'Jets'].Fill(sT)
    elif n_stealth_jets >= n_jets_min and n_stealth_jets > n_jets_max:
        histograms['sT_' + str(n_jets_max) + 'Jets'].Fill(sT)

print("\n") # proceed to next line after progress bar
# Scale histograms
normValues = {}
for i in range(n_jets_min, n_jets_max + 1):
    hist_name = 'sT_' + str(i) + 'Jets'
    norm_bin_start = histograms[hist_name].GetXaxis().FindBin(inputArguments.sTNormRangeMin)
    norm_bin_end = histograms[hist_name].GetXaxis().FindBin(inputArguments.sTNormRangeMax)
    normValues[i] = histograms[hist_name].Integral(norm_bin_start, norm_bin_end)
    histograms[hist_name].Scale(1.0 / normValues[i])

# Plot histograms
c_sT = ROOT.TCanvas('c_sT', '', 580, 620)
c_sT.SetBorderSize(0)
c_sT.SetFrameBorderMode(0)
ROOT.gStyle.SetTitleBorderSize(0)
ROOT.gStyle.SetOptStat(0)
p_top = ROOT.TPad('p_top', '', 0.005, 0.27, 0.995, 0.995)
p_bottom = ROOT.TPad('p_bottom', '', 0.005, 0.005, 0.995, 0.27)
p_top.Draw()
p_bottom.Draw()
p_top.SetMargin(12.0e-02, 3.0e-02, 5.0e-03, 2.0e-02)
p_bottom.SetMargin(12.0e-02, 3.0e-02, 29.0e-02, 4.0e-02)
p_top.SetTicky()
p_bottom.SetTicky()
p_bottom.SetGridy()
p_top.cd()
ROOT.gPad.SetLogy()

#Draw histograms
line_colors = [
    ROOT.kRed+1, ROOT.kGreen-3, ROOT.kAzure-2, ROOT.kOrange-3, ROOT.kGray
    ]
hist_name_0 = 'sT_' + str(n_jets_min) + 'Jets'
histograms[hist_name_0].GetYaxis().SetRangeUser(2.0e-4, 9.0)
histograms[hist_name_0].GetXaxis().SetTitleOffset(1.1)
histograms[hist_name_0].SetLineColor(line_colors[0])
histograms[hist_name_0].Draw('E')
for i in range(n_jets_min + 1, n_jets_max + 1):
    hist_name = 'sT_' + str(i) + 'Jets'
    histograms[hist_name].SetLineColor(line_colors[i - n_jets_min])
    histograms[hist_name].Draw('SAME E')
    c_sT.Update()

#Draw legend and labels
legend = ROOT.TLegend(0.75, 0.65, 0.86, 0.92)
for i in range(n_jets_min, n_jets_max):
    hist_name = 'sT_' + str(i) + 'Jets'
    legend.AddEntry(histograms[hist_name], str(i) + ' jets')
legend.AddEntry(histograms['sT_' + str(n_jets_max) + 'Jets'],
                '#geq ' + str(n_jets_max) + ' jets')
legend.SetBorderSize(0)
legend.Draw()

# Draw ratios
p_bottom.cd()
f_unity = ROOT.TF1('f_unity', '[0]', sT_min, sT_max)
f_unity.SetTitle("")
f_unity.SetParameter(0, 1.0)
f_unity.GetXaxis().SetLabelSize(0.1)
f_unity.GetXaxis().SetTickLength(0.1)
f_unity.GetXaxis().SetTitle('S_{T} (GeV)')
f_unity.GetXaxis().SetTitleOffset(1.14)
f_unity.GetXaxis().SetTitleSize(0.12)
f_unity.GetYaxis().SetLabelSize(0.1)
f_unity.GetYaxis().SetNdivisions(305)
f_unity.GetYaxis().SetRangeUser(0.25, 4.0)
f_unity.GetYaxis().SetTickLength(0.04)
f_unity.GetYaxis().SetTitle('n_{j} / n_{j} = ' + str(n_jets_min))
f_unity.GetYaxis().SetTitleSize(0.11)
f_unity.GetYaxis().SetTitleOffset(0.5)
f_unity.SetLineStyle(4)
f_unity.Draw()
graphsToPlot = {}
hist_name_toCompare = 'sT_' + str(inputArguments.nJetsNorm) + 'Jets'
for i in range(n_jets_min, n_jets_max + 1):
    if (i == inputArguments.nJetsNorm): continue
    hist_name = 'sT_' + str(i) + 'Jets'
    graphsToPlot[i] = make_ratio_graph('gae_' + str(i) + 'Jets', histograms[hist_name], histograms[hist_name_toCompare])
    graphsToPlot[i].SetMarkerStyle(20)
    graphsToPlot[i].SetMarkerColor(line_colors[i - n_jets_min])
    graphsToPlot[i].SetLineColor(line_colors[i - n_jets_min])
    graphsToPlot[i].SetMarkerSize(0.9)
    graphsToPlot[i].Draw('P SAME')
    c_sT.Update()
c_sT.SaveAs("analysis/plot_sT_{outputFilesSuffix}.png".format(outputFilesSuffix=inputArguments.outputFilesSuffix))
c_sT.Write()

ratioTH1Histograms = {}
chiSqValues = {}
for i in range(n_jets_min, n_jets_max + 1):
    if (i == inputArguments.nJetsNorm): continue
    hist_name = 'sT_' + str(i) + 'Jets'
    ratioTH1Histograms[i] = ROOT.TH1F("h_ratio_" + hist_name, ";S_{T} (GeV);AU", n_sT_bins, sT_min, sT_max)
    ratioTH1Histograms[i].Sumw2()
    ratioTH1Histograms[i].Divide(histograms[hist_name], histograms[hist_name_toCompare])
    ratios = []
    ratioErrors = []
    for sTBinCounter in range(1, 1 + n_sT_bins):
        ratios.append(ratioTH1Histograms[i].GetBinContent(sTBinCounter))
        ratioErrors.append(ratioTH1Histograms[i].GetBinError(sTBinCounter))
    chiSqValues[i] = getRatioChiSq(ratios, ratioErrors)/(n_sT_bins-1)

chiSqFile = open("analysis/chiSqRatios_{outputFilesSuffix}.txt".format(outputFilesSuffix=inputArguments.outputFilesSuffix), 'w')
for i in range(n_jets_min, n_jets_max + 1):
    if (i == inputArguments.nJetsNorm): continue
    chiSqFile.write('nJets = ' + str(i) + ': reduced chi_sq = ' + str(chiSqValues[i]) + '\n')
chiSqFile.close()

normValuesFile = open("analysis/normRatios_{outputFilesSuffix}.txt".format(outputFilesSuffix=inputArguments.outputFilesSuffix), 'w')
for i in range(n_jets_min, n_jets_max + 1):
    normValuesFile.write(str(i) + "    " + str(normValues[inputArguments.nJetsNorm]/normValues[i]) + '\n')
normValuesFile.close()

unbinnedRooSet = ROOT.RooDataSet("inputData", "inputData", normTree, ROOT.RooArgSet(rooVar_sT))
kernels = {"NoMirror": ROOT.RooKeysPdf.NoMirror, "MirrorLeft": ROOT.RooKeysPdf.MirrorLeft, "MirrorRight": ROOT.RooKeysPdf.MirrorRight, "MirrorBoth": ROOT.RooKeysPdf.MirrorBoth, "MirrorAsymLeft": ROOT.RooKeysPdf.MirrorAsymLeft, "MirrorAsymLeftRight": ROOT.RooKeysPdf.MirrorAsymLeftRight, "MirrorAsymRight": ROOT.RooKeysPdf.MirrorAsymRight, "MirrorLeftAsymRight": ROOT.RooKeysPdf.MirrorLeftAsymRight, "MirrorAsymBoth": ROOT.RooKeysPdf.MirrorAsymBoth}
rooKernelFunctions = {}
for kernelType in kernels.keys():
    print("Defining fit for kernel type: " + kernelType)
    rooKernelFunctions[kernelType] = ROOT.RooKeysPdf("rooKernelFunction_" + kernelType, "rooKernelFunction_" + kernelType, rooVar_sT, unbinnedRooSet, kernels[kernelType])
    sTFrame = rooVar_sT.frame(sT_min, sT_max, inputArguments.n_sTBins)
    unbinnedRooSet.plotOn(sTFrame)
    rooKernelFunctions[kernelType].plotOn(sTFrame)
    c_sTUnbinnedFit = ROOT.TCanvas('c_sTUnbinnedFit_' + kernelType, 'c_sTUnbinnedFit_' + kernelType, 1024, 768)
    c_sTUnbinnedFit.SetBorderSize(0)
    c_sTUnbinnedFit.SetFrameBorderMode(0)
    sTFrame.Draw()
    c_sTUnbinnedFit.SaveAs("analysis/plot_sT_UnbinnedFit_{outputFilesSuffix}_{kernelType}.png".format(outputFilesSuffix=inputArguments.outputFilesSuffix, kernelType=kernelType))
    c_sTUnbinnedFit.Write()

normTree.Write()
file_out.Write()
file_out.Close()

# for sTBackgroundFunctionName in sTBackgroundFunctionNames:
#     rooPDFs[sTBackgroundFunctionName].fitTo(unbinnedRooHist)

# rooVar_decayParameter.Print()
# rooVar_logTermCoefficient.Print()
# rooVar_expCoefficient.Print()

sw.Stop()
print ('Real time: ' + str(sw.RealTime() / 60.0) + ' minutes')
print ('CPU time:  ' + str(sw.CpuTime() / 60.0) + ' minutes')
