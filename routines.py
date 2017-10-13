############################################
# Created by Henri Petrow 2017
# Lappeenranta University of Technology
###########################################


import ROOT as r
import math
import time
import matplotlib.pyplot as plt
import numpy
import csv
from test_system_functions import *
from calibration_routines import *
from datapacket_routines import *
from trigger_routines import *
from generator import *


def scurve_all_ch_execute(obj, scan_name, arm_dac=100, ch=[0, 127], ch_step=1, configuration="yes", dac_range=[200, 240], delay=10, bc_between_calpulses=4000, pulsestretch=7, latency=0, cal_phi=0,folder="scurve"):
    start = time.time()

    modified = scan_name.replace(" ", "_")
    file_name = "./routines/%s/FPGA_instruction_list.txt" % modified

    # scan either all of the channels or just the one defined by ch.
    start_ch = ch[0]
    stop_ch = ch[1]

    start_dac_value = dac_range[0]
    stop_dac_value = dac_range[1]
    samples_per_dac_value = 100

    # Create the instructions for the specified scan values.
    steps = stop_dac_value - start_dac_value
    if configuration == "yes":
        instruction_text = []
        instruction_text.append("1 Send SCOnly")
        instruction_text.append("1 Write CAL_MODE 1")
        instruction_text.append("400 Write CAL_DAC %d" % start_dac_value)
        instruction_text.append("500 Send EC0")
        instruction_text.append("1 Send RunMode")
        instruction_text.append("1000 Repeat %d" % steps)
        instruction_text.append("1000 Send_Repeat CalPulse_LV1A %d %d %d" % (samples_per_dac_value, bc_between_calpulses, delay))
        instruction_text.append("1000 Send SCOnly")
        instruction_text.append("1000 Write CAL_DAC 1")
        instruction_text.append("200 Send RunMode")
        instruction_text.append("1 End_Repeat")
        instruction_text.append("1 Send SCOnly")

        # Write the instructions to the file.
        output_file_name = "./routines/%s/instruction_list.txt" % modified
        with open(output_file_name, "w") as mfile:
            for item in instruction_text:
                mfile.write("%s\n" % item)

        # Generate the instruction list for the FPGA.
        generator(scan_name, obj.write_BCd_as_fillers, obj.register)

        # Set the needed registers.
        obj.set_fe_nominal_values()

    obj.register[131].TP_FE[0] = 7
    obj.write_register(131)

    register[137].LAT[0] = latency
    obj.write_register(137)

    obj.register[130].DT[0] = 0
    obj.write_register(130)

    register[138].CAL_PHI[0] = cal_phi
    register[138].CAL_MODE[0] = 1
    obj.write_register(138)

    obj.register[132].PT[0] = 15
    obj.register[132].SEL_COMP_MODE[0] = 1
    obj.write_register(132)

    obj.register[135].ZCC_DAC[0] = 10
    obj.register[135].ARM_DAC[0] = arm_dac
    obj.write_register(135)

    obj.register[139].CAL_DUR[0] = 200
    obj.write_register(139)

    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    obj.register[129].ST[0] = 0
    obj.register[129].PS[0] = pulsestretch
    obj.write_register(129)

    if configuration == "yess":
        # Find the charge of the CAL_DAC steps with external ADC. (Not yet used.)
        if all([v == 0 for v in obj.cal_dac_fc_values]):
            print 'Calibration pulse steps are not calibrated. Running calibration...'
            cal_dac_steps(obj)

    charge_values = obj.cal_dac_fc_values[start_dac_value:stop_dac_value]
    charge_values.reverse()

    cal_dac_values = range(start_dac_value, stop_dac_value)
    cal_dac_values.reverse()
    cal_dac_values[:] = [255 - x for x in cal_dac_values]
    all_ch_data = []
    all_ch_data.append(["", "255-CAL_DAC"])
    data_line = []
    data_line.append("Channel")
    data_line.extend(cal_dac_values)
    all_ch_data.append(data_line)
    for k in range(start_ch, stop_ch+1, ch_step):
        print "Channel: %d" % k
        while True:
            obj.register[k].cal[0] = 1
            obj.write_register(k)

            scurve_data = []
            output = obj.interfaceFW.launch(obj.register, file_name, obj.COM_port, 1)
            if output[0] == "Error":
                text = "%s: %s\n" % (output[0], output[1])
                obj.add_to_interactive_screen(text)
            else:
                hits = 0
                for i in output[3]:
                    if i.type == "IPbus":
                        scurve_data.append(hits)
                        hits = 0
                    elif i.type == "data_packet":

                        if i.data[127 - k] == "1":
                            hits += 1
            scurve_data = scurve_data[2:]
            scurve_data.reverse()
            print scurve_data
            # Check that there is enough data and it is not all zeroes.
            if len(scurve_data) != steps:
                print "Not enough values, trying again."
                continue
            if len(scurve_data) == steps:
                break

        # Unset the calibration to the channel.
        obj.register[k].cal[0] = 0
        obj.write_register(k)
        # time.sleep(0.1)

        # Modify the decoded data.
        saved_data = []
        saved_data.append(k)

        saved_data.extend(scurve_data)
        all_ch_data.append(saved_data)

    # Save the results.
    timestamp = time.strftime("%Y%m%d_%H%M")
    text = "Results were saved to the folder:\n %s \n" % folder
    filename = "%s/%s/%sS-curve_data.csv" % (obj.data_folder, folder, timestamp)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            print "Unable to create directory"
    with open(filename, "wb") as f:
        writer = csv.writer(f)
        writer.writerows(all_ch_data)
    obj.add_to_interactive_screen(text)
    # Analyze data.
    mean_th = scurve_analyze(obj, all_ch_data,folder)
    print "Mean: %f" % mean_th
    stop = time.time()
    run_time = (stop - start) / 60
    text = "Run time (minutes): %f\n" % run_time
    obj.add_to_interactive_screen(text)
    threshold = mean_th
    return [threshold, all_ch_data]


def scurve_analyze(obj, scurve_data,folder):
    timestamp = time.strftime("%d.%m.%Y %H:%M")

    r.gROOT.SetBatch(True)

    dac_values = scurve_data[1][1:]

    Nhits_h = {}
    Nev_h = {}

    for i in range(2, len(scurve_data)):
        diff = []

        data = scurve_data[i][1:]
        channel = scurve_data[i][0]

        Nhits_h[channel] = r.TH1D('Nhits%i_h'%(channel),'Nhits%i_h'%(channel),256,-0.5,255.5)
        Nev_h[channel] = r.TH1D('Nev%i_h'%(channel),'Nev%i_h'%(channel),256,-0.5,255.5)

        for j,Nhits in enumerate(data): 
            Nhits_h[channel].AddBinContent(dac_values[j]-1,Nhits)
            Nev_h[channel].AddBinContent(dac_values[j]-1,100)
            pass

        pass
    timestamp = time.strftime("%Y%m%d_%H%M%s")
    filename = '%s/%s/scurves%s.root' %(obj.data_folder, folder,timestamp)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            print "Unable to create directory"

    outF = r.TFile(filename, 'RECREATE')

    enc_h = r.TH1D('enc_h', 'ENC of all Channels;ENC [DAC Units];Number of Channels', 100, 0.0, 1.0)
    thr_h = r.TH1D('thr_h', 'Threshold of all Channels;ENC [DAC Units];Number of Channels', 160, 0.0, 80.0)
    chi2_h = r.TH1D('chi2_h', 'Fit #chi^{2};#chi^{2};Number of Channels / 0.001', 100, 0.0, 1.0)
    enc_list = []
    scurves_ag = {}
    txtOutF = open('%s/%s/scurveFits%s.dat'%(obj.data_folder, folder,timestamp),'w')
    txtOutF.write('CH/I:thr/D:enc/D\n')
    print 'Fitting Scurves'
    for ch in Nhits_h:
        scurves_ag[ch] = r.TGraphAsymmErrors(Nhits_h[ch], Nev_h[ch])
        scurves_ag[ch].SetName('scurve%i_ag' % ch)
        fit_f = fitScurve(scurves_ag[ch])
        txtOutF.write('%i\t%f\t%f\n'%(ch,fit_f.GetParameter(0),fit_f.GetParameter(1)*obj.cal_dac_m+obj.cal_dac_b))
        scurves_ag[ch].Write()
        thr_h.Fill(fit_f.GetParameter(0))
        enc_h.Fill(fit_f.GetParameter(1))
        enc_list.append(fit_f.GetParameter(1))
        chi2_h.Fill(fit_f.GetChisquare())
        pass
    txtOutF.close()
    chENC_t = r.Tree('chENC_t','Tree with noise data')
    chENC_t.ReadFile('%s/%s/scurveFits%s.dat'%(obj.data_folder, folder,timestamp))

    cc = r.TCanvas('canv','canv',1000,1000)
    cc.cd()

    chENC_t.Draw('enc:CH')
    cc.SaveAs('%s/%s/chENC_%s.png'%(obj.data_folder, folder,timestamp))

    meanThr = thr_h.GetMean()
    drawHisto(thr_h,cc,'%s/%s/threshHiso%s.png' %(obj.data_folder, folder,timestamp))
    #print "Mean: %f" % thr_mean
    thr_h.Write()
    drawHisto(enc_h, cc, '%s/%s/encHisto%s.png' %(obj.data_folder, folder,timestamp))
    enc_h.Write()
    drawHisto(chi2_h, cc, '%s/%s/chi2Histo%s.png' %(obj.data_folder, folder,timestamp))
    chi2_h.Write()
    outF.Close()
    #fig = plt.figure()
    #channels = range(0, 128)
    #plt.plot(channels, enc_list)
    #plt.ylim(0, 1)
    #plt.grid(True)
    #plt.show()
    #fig.savefig("enc_channels.png")
    return meanThr


def drawHisto(hist, canv, filename):
    canv.cd()
    hist.SetLineWidth(2)
    hist.GetXaxis().CenterTitle()
    hist.GetYaxis().CenterTitle()
    hist.Draw()
    canv.SaveAs(filename)
    

def fitScurve(scurve_g):
    import copy
    erf_f = r.TF1('erf_f','0.5*TMath::Erf((x-[0])/(TMath::Sqrt(2)*[1]))+0.5',0.0,80.0)
    minChi2 = 9999.9
    bestI = -1
    for i in range(20):
        erf_f.SetParameter(0,1.0*i+15.0)
        erf_f.SetParameter(1,2.0)
        scurve_g.Fit(erf_f,'Q')
        chi2 = erf_f.GetChisquare()
        if chi2 < minChi2 and chi2 > 0.0:
            bestI = i
            minChi2 = chi2
            bestFit_f = copy.deepcopy(erf_f)
            pass
        pass
    erf_f.SetParameter(0,2.0*bestI+1.0)
    erf_f.SetParameter(1,2.0)
    scurve_g.Fit(erf_f,'Q')
    return bestFit_f


def scan_execute(obj, scan_name, plot=1,):

    start = time.time()

    reg_values = []
    scan_values0 = []
    scan_values1 = []
    modified = scan_name.replace(" ", "_")
    file_name = "./routines/%s/FPGA_instruction_list.txt" % modified

    output = obj.interfaceFW.launch(obj.register, file_name, obj.COM_port, 0)

    if output[0] == "Error":
        text = "%s: %s\n" % (output[0], output[1])
        obj.add_to_interactive_screen(text)
    else:
        adc_flag = 0
        reg_value = 0
        for i in output[0]:
            if i.type_ID == 0:
                if adc_flag == 0:
                    first_adc_value = int(''.join(map(str, i.data)), 2)
                    adc_flag = 1
                else:
                    second_adc_value = int(''.join(map(str, i.data)), 2)
                    # scan_values0.append(obj.adc0M * first_adc_value + obj.adc0B)
                    # scan_values1.append(obj.adc1M * second_adc_value + obj.adc1B)
                    scan_values0.append(first_adc_value)
                    scan_values1.append(second_adc_value)
                    reg_values.append(reg_value)
                    reg_value += 1
                    adc_flag = 0
        for i in output[4]:
            print i

    # Save the results.
    data = [reg_values,scan_values0,scan_values1]
    timestamp = time.strftime("%Y%m%d%H%M")
    filename = "%s/dac_scans/%s_%s_scan_data.dat" % (obj.data_folder, timestamp, modified)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            print "Unable to create directory"
    text = "Results were saved to the folder:\n %s \n" % filename

    outF = open(filename, "w")
    outF.write("regVal/I:ADC0/I:ADC1/I\n")
    for i,regVal in enumerate(reg_values):
        outF.write('%i\t%i\t%i\n'%(regVal,scan_values0[i],scan_values1[i]))
        pass
    outF.close()
    
    obj.add_to_interactive_screen(text)
    filename = "%s/dac_scans/%s_%s_scan.png" % (obj.data_folder, timestamp, modified)
    if plot == 1:
        nr_points = len(scan_values0)
        x = range(0, nr_points)
        #fig = plt.figure(1)
        plt.clf()
        plt.plot(x, scan_values0, label="ADC0")
        plt.plot(x, scan_values1, label="ADC1")
        plt.ylabel('ADC counts')
        plt.xlabel('DAC counts')
        plt.legend()
        plt.title(modified)
        plt.grid(True)
        plt.savefig(filename)
        #plt.close(fig)

    stop = time.time()
    run_time = (stop - start) / 60
    text = "Scan duration: %f min\n" % run_time
    obj.add_to_interactive_screen(text)

    return output


def scurve_analyze_one_ch(scurve_data):
    dac_values = scurve_data[1][1:]

    Nhits_h = r.TH1D('Nhitsi_h', 'Nhitsi_h', 256, -0.5, 255.5)
    Nev_h = r.TH1D('Nevi_h', 'Nevi_h', 256, -0.5, 255.5)

    data = scurve_data[2][1:]

    for j, Nhits in enumerate(data):
        Nhits_h.AddBinContent(dac_values[j] - 1, Nhits)
        Nev_h.AddBinContent(dac_values[j] - 1, 100)

    scurves_ag = r.TGraphAsymmErrors(Nhits_h, Nev_h)
    scurves_ag.SetName('scurvei_ag')
    fit_f = fitScurve(scurves_ag)
    thr_h = fit_f.GetParameter(0)

    return thr_h













