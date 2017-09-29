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
from generator import *


def adjust_local_thresholds(obj):
    start = time.time()
    # Measure the mean threshold of the channels, that will be used as a target.
    mean_threshold = scurve_all_ch_execute(obj, "S-curve all ch")
    print "Found the mean threshold for the 128 channels: %f" % mean_threshold
    for k in range(0, 128):
        obj.send_reset()
        obj.send_sync()
        thresholds = []
        diff_values = []

        # Read the current dac values
        #obj.read_register(k)
        print "Adjusting the channel %d local arm_dac." % k
        output = scurve_all_ch_execute(obj, "S-curve all ch", arm_dac=100, ch=[k,k], configuration="no")
        threshold = output[0]
        print "Threshold: %f, target: %f. DAC: %d" % (threshold, mean_threshold, obj.register[k].arm_dac[0])
        previous_diff = abs(mean_threshold - threshold)
        previous_value = 0
        thresholds.append(threshold)
        diff_values.append(previous_diff)
        if threshold < mean_threshold:
            print "->Value too low, increase arm_dac register."
            obj.register[k].arm_dac[0] = 0
            obj.write_register(k)
            max_value = 63
            direction = "up"
        if threshold > mean_threshold:
            print "->Value too high, decrease arm_dac register."
            obj.register[k].arm_dac[0] = 64
            obj.write_register(k)
            max_value = 128
            direction = "down"

        while True:
            obj.register[k].arm_dac[0] += 1
            obj.write_register(k)

            output = scurve_all_ch_execute(obj, "S-curve all ch", arm_dac=100, ch=[k,k], configuration="no")
            threshold = output[0]
            print "Threshold: %f, target: %f. DAC: %d" % (threshold, mean_threshold, obj.register[k].arm_dac[0])
            thresholds.append(threshold)
            new_diff = abs(mean_threshold - threshold)
            diff_values.append(new_diff)
            print thresholds
            print diff_values
            if direction == "up" and threshold > mean_threshold:
                if previous_diff < new_diff:
                    print "->Difference increasing. Choose previous value: %d." % previous_value
                    obj.register[k].arm_dac[0] = previous_value
                print "-> Channel calibrated."
                break
            if direction == "down" and threshold < mean_threshold:
                if previous_diff < new_diff:
                    print "->Difference increasing. Choose previous value: %d." % previous_value
                    obj.register[k].arm_dac[0] = previous_value
                print "-> Channel calibrated."
                break

            previous_value = obj.register[k].arm_dac[0]
            previous_diff = new_diff

    # Save the channel calibration settings to a file.
    open("./data/channel_registers.dat", 'w').close()
    for register_nr in range(0, 128):
        data = []
        for x in register[register_nr].reg_array:
            data.extend(dec_to_bin_with_stuffing(x[0], x[1]))
        data = ''.join(str(e) for e in data)
        with open("./data/channel_registers.dat", "a") as mfile:
            mfile.write("%s\n" % data)

    stop = time.time()
    run_time = (stop - start) / 60
    print "Run time (minutes): %f\n" % run_time


def gain_measurement(obj,adc ="ext"):

    start = time.time()

    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    obj.register[133].Monitor_Sel[0] = 14
    obj.write_register(133)

    arm_dac_values = []
    extADC = []
    ADC0 = []
    ADC1 = []
    threshold_fc = []

    for arm_dac in range(100, 151, 10):
        arm_dac_values.append(arm_dac)
        obj.register[135].ARM_DAC[0] = arm_dac
        obj.write_register(135)
        time.sleep(1)
        extADC.append(obj.interfaceFW.ext_adc())
        # if not isinstance(extADC,(int, long)):
        #extADC.append(0)
        ADC0.append(obj.read_adc0())
        ADC1.append(obj.read_adc1())
        output = scurve_all_ch_execute(obj, "S-curve", arm_dac=arm_dac, ch=[41, 46], configuration="yes",
                                              dac_range=[200, 240], delay=50, bc_between_calpulses=2000, pulsestretch=7,
                                             latency=45, cal_phi=0, folder="gain_meas")
        threshold_fc.append(output[0])
    timestamp = time.strftime("%Y%m%d_%H%M")
    filename = "%s/%s/%sgain_measurement.dat" % (obj.data_folder, "gain_meas", timestamp)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            print "Unable to create directory"
    text = "Results were saved to the folder:\n %s \n" % filename

    outF = open(filename, "w")
    outF.write("arm_dac/I:ADC0/I:ADC1/I:extADC/I:thr_scurve/D\n")
    for i, armdac in enumerate(arm_dac_values):
        outF.write('%i\t%i\t%i\t%i\t%f\n' % (armdac, ADC0[i], ADC1[i], extADC[i],threshold_fc[i]))
        pass
    outF.close()

    stop = time.time()
    run_time = (stop - start) / 60
    print "Runtime: %f" % run_time
    # # Calculate the gain.
    # if adc == "ext":
    #     print "Thresholds in mV TH0: %f and TH1: %f" % (threshold_mv0, threshold_mv1)
    # else:
    #     print "Thresholds in dac counts TH0: %f and TH1: %f" % (threshold_mv0, threshold_mv1)
    # print "Thresholds in fC TH0: %f and TH1: %f" % (threshold_fc0, threshold_fc1)
    # gain = (threshold_mv1 - threshold_mv0)/(threshold_fc1 - threshold_fc0)
    # print gain


def scurve_all_ch_execute(obj, scan_name, arm_dac=100, ch=[0, 127], ch_step=1, configuration="yes", dac_range=[200, 240], delay=10, bc_between_calpulses=4000, pulsestretch=7, latency=0, cal_phi=0,folder="scurve"):
    start = time.time()

    # if obj.Iref == 0:
    #     # Adjust the global reference current of the chip.
    #     iref_adjust(obj)

    modified = scan_name.replace(" ", "_")
    file_name = "./routines/%s/FPGA_instruction_list.txt" % modified

    # scan either all of the channels or just the oe defined by ch.

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

    # if ch = "all":
    cal_dac_values = range(start_dac_value, stop_dac_value)
    cal_dac_values.reverse()
    cal_dac_values[:] = [255 - x for x in cal_dac_values]
    all_ch_data = []
    all_ch_data.append(["", "255-CAL_DAC"])
    # all_ch_data.append(["Channel", 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35])
    data_line = []
    data_line.append("Channel")
    data_line.extend(cal_dac_values)
    all_ch_data.append(data_line)
    for k in range(start_ch, stop_ch+1, ch_step):
        print "Channel: %d" % k
        while True:
            # Set calibration to right channel.
            # print "Set register."
            obj.register[k].cal[0] = 1
            obj.write_register(k)
            # time.sleep(0.1)
            # print "Register set."
            scurve_data = []
            # Run the predefined routine.
            # print "launch routine"
            output = obj.interfaceFW.launch(obj.register, file_name, obj.COM_port, 1)
            # print "routine done."
            # Check the received data from the routine.
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
            # if len(scurve_data) == 20 and scurve_data[-3] != 0:
            #     break
            if len(scurve_data) == steps:
                break

        # Unset the calibration to the channel.
        # print "unset register."
        obj.register[k].cal[0] = 0
        # print "register unset."
        obj.write_register(k)
        # time.sleep(0.1)

        # Modify the decoded data.
        saved_data = []
        saved_data.append(k)
        #scurve = scurve_data[2:]
        #scurve.reverse()
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


def calibration(obj):
    start = time.time()
    output = generator("Calibration", 0, obj.register)
    for i in output[0]:
        print i
    file_name = "./routines/Calibration/FPGA_instruction_list.txt"
    output = obj.interfaceFW.launch(obj.register, file_name, obj.COM_port)

    cal_values = []

    if output[0] == "Error":
        text = "%s: %s\n" % (output[0], output[1])
        obj.add_to_interactive_screen(text)
    else:
        flag = 0
        print len(output[0])
        for i in output[0]:
            if i.type_ID == 0:
                if flag == 0:
                    base_value = int(''.join(map(str, i.data)), 2)
                    print "Base value: %d" % base_value
                    flag = 1
                else:
                    step_value = int(''.join(map(str, i.data)), 2)
                    print "Step value: %d" % step_value
                    cal_value = step_value - base_value
                    print "Cal value: %d" % cal_value
                    cal_values.append(cal_value)

    print cal_values


def cal_dac_steps(obj):

    start_dac_value = 0
    stop_dac_value = 255

    obj.register[133].Monitor_Sel[0] = 33
    obj.write_register(133)

    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(0.1)

    base_values = []
    step_values = []
    dac_values = []
    charge_values = []

    for i in range(start_dac_value, stop_dac_value+1):
        #newVal = raw_input("ready?")
        register[138].CAL_DAC[0] = i
        obj.write_register(138)
        time.sleep(0.1)

        register[138].CAL_SEL_POL[0] = 1
        obj.write_register(138)
        time.sleep(0.1)

        baseADC = obj.read_adc1()
        base = obj.adc1M*baseADC + obj.adc1B

        register[138].CAL_SEL_POL[0] = 0
        obj.write_register(138)
        time.sleep(0.1)

        stepADC = obj.read_adc1()
        step = obj.adc1M*stepADC + obj.adc1B

        difference = step-base
        charge = (difference/1000.0) * 100.0  # 100 fF capacitor.

        base_values.append(base)
        step_values.append(step)
        dac_values.append(255-i)
        charge_values.append(charge)
        print "DAC value: %d" % i
        print "Base value: %f mV, step value: %f mV" % (base, step)
        print "Difference: %f mV, CHARGE: %f fC" % (difference, charge)
        print "--------------------------------"

    # print dac_values
    # print charge_values
    obj.cal_dac_fc_values = charge_values
    return dac_values, base_values, step_values, charge_values


def iref_adjust(obj):

    # Read the current Iref dac value.
    obj.read_register(134)
    register[134].Iref[0] = 1
    obj.write_register(134)
    previous_value = 1

    # Set monitoring to Iref
    obj.register[133].Monitor_Sel[0] = 0
    obj.write_register(133)

    # Set RUN bit to activate analog part.
    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    previous_diff = 100
    text = "Adjusting the global reference current.\n"
    print text
    obj.add_to_interactive_screen(text)
    while True:

        time.sleep(1)
        output = obj.interfaceFW.ext_adc()
        if output == "Error":
            print "No response from ADC, aborting Iref adjustment."
            break
        print "Iref: %f, target: 100 mV. DAC: %d" % (output, register[134].Iref[0])
        new_diff = abs(100 - output)

        if previous_diff < new_diff:
            print "->Difference increasing. Choose previous value: %d." % previous_value
            register[134].Iref[0] = previous_value
            obj.Iref = previous_value
            obj.write_register(134)
            break
        previous_value = register[134].Iref[0]
        if output < 100:
            print "->Value too low, increase Iref register by 1."
            register[134].Iref[0] += 1
        else:
            print "->Value too high, decrease Iref register by 1."
            register[134].Iref[0] -= 1
        obj.write_register(134)
        previous_diff = new_diff

    obj.register[65535].RUN[0] = 0
    obj.write_register(65535)
    time.sleep(1)
    text = "- Iref adjusted.\n"
    print text
    obj.add_to_interactive_screen(text)


def adc_comparison(obj):

    obj.register[133].Monitor_Sel[0] = 34
    obj.write_register(133)

    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    int_adc_values = []
    ext_adc_values = []
    dac_values = []
    for i in range(0, 255):
        dac_values.append(i)
        print "->Measuring DAC value %d" %i
        register[142].PRE_VREF[0] = i
        obj.write_register(142)

        int_adc_value = obj.read_adc1()
        print "ADC1: %f" % int_adc_value
        int_adc_values.append(int_adc_value)

        ext_adc_value = obj.interfaceFW.ext_adc()
        print "ext. ADC: %f" % ext_adc_value
        ext_adc_values.append(ext_adc_value)

    obj.register[133].Monitor_Sel[0] = 0
    obj.write_register(133)

    obj.register[65535].RUN[0] = 0
    obj.write_register(65535)
    time.sleep(1)

    plt.plot(dac_values, ext_adc_values, label='EXT ADC')
    plt.plot(dac_values, int_adc_values, label='ADC1')
    plt.legend(loc='upper left')

    plt.xlabel('DAC[counts]')
    plt.ylabel('Voltage [mV]')
    plt.title('Ext ADC vs. Int ADC1')
    plt.grid(True)
    plt.show()


def scurve_execute(obj, scan_name):

    start = time.time()
    channel = 127
    # Set calibration to right channel.
    obj.register[channel].cal[0] = 1
    obj.write_register(channel)

    obj.set_fe_nominal_values()

    obj.register[130].DT[0] = 0
    obj.write_register(130)

    # register[138].CAL_MODE[0] = 2
    # obj.write_register(138)

    obj.register[132].SEL_COMP_MODE[0] = 0
    obj.write_register(132)

    # obj.register[134].Iref[0] = 27
    # obj.write_register(134)

    #obj.register[135].ZCC_DAC[0] = 10
    #obj.register[135].ARM_DAC[0] = 100
    #obj.write_register(135)

    obj.register[139].CAL_FS[0] = 0
    obj.register[139].CAL_DUR[0] = 200
    obj.write_register(139)

    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    obj.register[129].ST[0] = 0
    obj.register[129].PS[0] = 7
    obj.write_register(129)

    modified = scan_name.replace(" ", "_")
    file_name = "./routines/%s/FPGA_instruction_list.txt" % modified
    scurve_data = []

    output = obj.interfaceFW.launch(obj.register, file_name, obj.COM_port)
    if output[0] == "Error":
        text = "%s: %s\n" % (output[0], output[1])
        obj.add_to_interactive_screen(text)
    else:
        hits = 0
        dac = 38
        for i in output[3]:
            if i.type == "IPbus":
                dac -= 1
                scurve_data.append([dac, hits])
                hits = 0
            elif i.type == "data_packet":
                if i.data[127 - channel] == "1":
                    hits += 1

    text = "CAL_DAC|HITS \n"
    obj.add_to_interactive_screen(text)
    outF = open('routines/scurveData.dat','w')
    outF.write('CALDAC/I:NHits/I\n')
    for k in scurve_data[2:]:
        text = "%d %d\n" % (k[0], k[1])
        outF.write("%d\t%d\n" % (k[0], k[1]))
        obj.add_to_interactive_screen(text)
        pass
    outF.close()


    obj.register[channel].cal[0] = 0
    obj.write_register(channel)

    stop = time.time()
    run_time = (stop - start) / 60
    text = "Run time (minutes): %f" % run_time
    obj.add_to_interactive_screen(text)


def set_up_trigger_pattern(obj, option):

    trigger_pattern = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                       0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                       0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
                       0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
                       0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
                       0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
                       0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
                       0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    if option == 2:
        text = "Clearing trigger patterns\n"
        obj.add_to_interactive_screen(text)
        for k in range(0, 128):
            print "Clear channel: %d" % k
            obj.register[k].cal[0] = 0
            obj.write_register(k)
            time.sleep(0.1)
        obj.register[130].DT[0] = 0
        obj.write_register(130)

        obj.register[138].CAL_DAC[0] = 0
        obj.register[138].CAL_MODE[0] = 0
        obj.write_register(138)

        obj.register[132].SEL_COMP_MODE[0] = 0
        obj.write_register(132)

        obj.register[139].CAL_FS[0] = 0
        obj.register[139].CAL_DUR[0] = 0
        obj.write_register(139)

        obj.register[65535].RUN[0] = 0
        obj.write_register(65535)

        obj.register[129].ST[0] = 0
        obj.register[129].PS[0] = 0
        obj.write_register(129)
    else:

        text = "Setting trigger pattern.\n"
        obj.add_to_interactive_screen(text)
        for k in range(0, 128):
            print "Set channel:%d to: %d" % (k, trigger_pattern[k])
            obj.register[k].cal[0] = trigger_pattern[k]
            obj.write_register(k)

        obj.set_fe_nominal_values()
        print "Set FE nominal values."

        obj.register[130].DT[0] = 0
        obj.write_register(130)

        obj.register[138].CAL_DAC[0] = 200
        obj.register[138].CAL_MODE[0] = 1
        obj.write_register(138)
        print "Set CAL_DAC to: %d and CAL_MODE to: %d" % (obj.register[138].CAL_DAC[0], obj.register[138].CAL_MODE[0])

        obj.register[132].SEL_COMP_MODE[0] = 0
        obj.write_register(132)
        print "Set SEL_COMP_MODE to: %d" % obj.register[132].SEL_COMP_MODE[0]

        obj.register[134].Iref[0] = 27
        obj.write_register(134)
        print "Set Iref to: %d" % obj.register[134].Iref[0]

        obj.register[135].ZCC_DAC[0] = 10
        obj.register[135].ARM_DAC[0] = 100
        obj.write_register(135)
        print "Set ZCC_DAC to: %d and Set ARM_DAC to: %d" % (obj.register[135].ZCC_DAC[0], obj.register[135].ARM_DAC[0])

        obj.register[139].CAL_FS[0] = 3
        obj.register[139].CAL_DUR[0] = 100
        obj.write_register(139)
        print "Set CAL_FS to: %d and Set CAL_DUR to: %d" % (obj.register[139].CAL_FS[0], obj.register[139].CAL_DUR[0])

        obj.register[65535].RUN[0] = 1
        obj.write_register(65535)
        print "Set RUN to: %d" % obj.register[65535].RUN[0]

        obj.register[129].ST[0] = 1
        obj.register[129].PS[0] = 0
        obj.write_register(129)
        print "Set ST to: %d and Set PS to: %d" % (obj.register[129].ST[0], obj.register[129].PS[0])

        text = "-Using self triggering.\n-With CalPulse from the FCC-tab you can trigger the channels."
        obj.add_to_interactive_screen(text)


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
        #text = "DAC scan values:\n"
        #obj.add_to_interactive_screen(text)
        adc_flag = 0
        #text = "%s|ADC0|ADC1|\n" % scan_name[:-5]
       # obj.add_to_interactive_screen(text)
        reg_value = 0
        for i in output[0]:
            if i.type_ID == 0:
                if adc_flag == 0:
                    first_adc_value = int(''.join(map(str, i.data)), 2)
                    adc_flag = 1
                else:
                    second_adc_value = int(''.join(map(str, i.data)), 2)
                    #text = "%d %d %d\n" % (reg_value, first_adc_value, second_adc_value)
                    #obj.add_to_interactive_screen(text)
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

    if plot == 1:
        nr_points = len(scan_values0)
        x = range(0, nr_points)
        fig = plt.figure(1)
        plt.plot(x, scan_values0, label="ADC0")
        plt.plot(x, scan_values1, label="ADC1")
        plt.ylabel('ADC counts')
        plt.xlabel('DAC counts')
        plt.legend()
        plt.title(modified)
        plt.grid(True)
        fig.show()

    stop = time.time()
    run_time = (stop - start) / 60
    text = "Scan duration: %f min\n" % run_time
    obj.add_to_interactive_screen(text)

    return output


def scan_cal_dac_fc(obj, scan_name):

    start = time.time()

    modified = scan_name.replace(" ", "_")
    modified = modified.replace(",", "_")

    dac_values, base_values, step_values, charge_values = cal_dac_steps(obj)

    # Plot the results.
    fig = plt.figure(1)
    plt.plot(dac_values, charge_values, label="CAL_DAC")
    plt.ylabel('Charge [fC]')
    plt.xlabel('DAC counts (255-CAL_DAC)')
    plt.legend()
    plt.title(modified)
    plt.grid(True)
    fig.show()

    # Save the results.
    #dac_values.insert(0,"DAC count 255-CAL_DAC")
    #charge_values.insert(0,"Charge [fC]")

    data = [dac_values, charge_values]
    timestamp = time.strftime("%Y%m%d%H%M")
    folder = "./results/"
    filename = "%s%s_%s_scan_data.dat" % (folder, timestamp, modified)

    outF = open(filename, "w")
    outF.write("dacValue/D:baseV/D:stepV/D:Q/D\n")
    for i,dacVal in enumerate(dac_values):
        outF.write('%f\t%f\t%f\t%f\n'%(dacVal,base_values[i],step_values[i],charge_values[i]))
        pass
    outF.close()
    text = "Results were saved to the file:\n %s \n" % filename

    obj.add_to_interactive_screen(text)


    stop = time.time()
    run_time = (stop - start) / 60
    text = "Scan duration: %f min\n" % run_time
    obj.add_to_interactive_screen(text)


def continuous_trigger(obj):

        obj.set_fe_nominal_values()
        print "Set FE nominal values."

        obj.register[130].DT[0] = 0
        obj.write_register(130)

        obj.register[138].CAL_DAC[0] = 200
        obj.register[138].CAL_MODE[0] = 1
        obj.write_register(138)
        print "Set CAL_DAC to: %d and CAL_MODE to: %d" % (obj.register[138].CAL_DAC[0], obj.register[138].CAL_MODE[0])

        obj.register[132].SEL_COMP_MODE[0] = 0
        obj.write_register(132)
        print "Set SEL_COMP_MODE to: %d" % obj.register[132].SEL_COMP_MODE[0]

        obj.register[134].Iref[0] = 27
        obj.write_register(134)
        print "Set Iref to: %d" % obj.register[134].Iref[0]

        obj.register[135].ZCC_DAC[0] = 10
        obj.register[135].ARM_DAC[0] = 100
        obj.write_register(135)
        print "Set ZCC_DAC to: %d and Set ARM_DAC to: %d" % (obj.register[135].ZCC_DAC[0], obj.register[135].ARM_DAC[0])

        obj.register[139].CAL_FS[0] = 3
        obj.register[139].CAL_DUR[0] = 100
        obj.write_register(139)
        print "Set CAL_FS to: %d and Set CAL_DUR to: %d" % (obj.register[139].CAL_FS[0], obj.register[139].CAL_DUR[0])

        obj.register[65535].RUN[0] = 1
        obj.write_register(65535)
        print "Set RUN to: %d" % obj.register[65535].RUN[0]

        obj.register[129].ST[0] = 0
        obj.register[129].PS[0] = 0
        obj.write_register(129)
        print "Set ST to: %d and Set PS to: %d" % (obj.register[129].ST[0], obj.register[129].PS[0])
        obj.send_fcc("RunMode")
        while True:
            obj.send_fcc("CalPulse")
            time.sleep(0.000000025)


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


def scurve_analyze_old(obj, scurve_data, folder):
    timestamp = time.strftime("%d.%m.%Y %H:%M")
    full_data = []
    mean_list = []
    rms_list = []
    full_data.append([""])
    full_data.append(["Differential data"])
    full_data.append(["", "255-CAL_DAC"])
    # full_data.append(
    #    ["Channel", 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, "mean", "RMS"])
    dac_values = scurve_data[1][1:]

    fig = plt.figure(figsize=(10, 20))
    sub1 = plt.subplot(411)

    for i in range(2, 130):
        diff = []

        mean_calc = 0
        summ = 0
        data = scurve_data[i][1:]
        channel = scurve_data[i][0]

        diff.append(channel)
        diff.append("")
        l = 0
        for j in data:
            if l != 0:
                diff_value = j - previous_value
                diff.append(diff_value)
                mean_calc += dac_values[l] * diff_value
                summ += diff_value
            previous_value = j
            l += 1
        if summ == 0:
            mean = 0
        else:
            mean = mean_calc / float(summ)
        mean_list.append(mean)
        l = 1
        rms = 0
        for r in diff[2:]:
            rms += r * (mean - dac_values[l]) ** 2
            l += 1

        if summ == 0:
            rms = 0
        else:
            rms = math.sqrt(rms / summ)
        rms_list.append(rms)
        diff.append(mean)
        diff.append(rms)
        full_data.append(diff)
        plt.plot(dac_values, data)

    rms_mean = numpy.mean(rms_list)
    rms_rms = numpy.std(rms_list)

    mean_mean = numpy.mean(mean_list)
    mean_rms = numpy.std(mean_list)

    sub1.set_xlabel('255-CAL_DAC')
    sub1.set_ylabel('%')
    sub1.set_title('S-curves of all channels')
    sub1.grid(True)

    text = "%s \n S-curves, 128 channels, N=100, HG, 25 ns." % timestamp
    sub1.text(25, 140, text, horizontalalignment='center', verticalalignment='center')

    sub2 = plt.subplot(413)
    sub2.plot(range(0, 128), rms_list)
    sub2.set_xlabel('Channel')
    sub2.set_ylabel('RMS')
    sub2.set_title('RMS of all channels')
    sub2.grid(True)
    text = "mean: %.2f RMS: %.2f" % (rms_mean, rms_rms)
    y_placement = max(rms_list) - 0.05
    sub2.text(10, y_placement, text, horizontalalignment='center', verticalalignment='center', bbox=dict(alpha=0.5))

    sub3 = plt.subplot(412)
    sub3.plot(range(0, 128), mean_list)
    sub3.set_xlabel('Channel')
    sub3.set_ylabel('255-CAL_DAC')
    sub3.set_title('mean of all channels')
    sub3.grid(True)
    text = "Mean: %.2f RMS: %.2f" % (mean_mean, mean_rms)
    y_placement = max(mean_list) - 1
    sub3.text(10, y_placement, text, horizontalalignment='center', verticalalignment='center', bbox=dict(alpha=0.5))

    sub4 = plt.subplot(427)
    sub4.hist(mean_list, bins=30)
    sub3.grid(True)


    sub5 = plt.subplot(428)
    sub5.hist(rms_list, bins=30)
    sub3.grid(True)

    fig.subplots_adjust(hspace=.5)

    timestamp = time.strftime("%Y%m%d_%H%M")

    fig.savefig("%s%sS-curve_plot.pdf" % (folder, timestamp))

    with open("%s%sS-curve_data.csv" % (folder, timestamp), "ab") as f:
        writer = csv.writer(f)
        writer.writerows(full_data)

    text = "Results were saved to the folder:\n %s \n" % folder
    obj.add_to_interactive_screen(text)
    return 0


def concecutive_triggers(obj, nr_loops=25):
    timestamp = time.strftime("%Y%m%d_%H%M")
    scan_name = "Consecutive_Triggers"
    file_name = "./routines/%s/FPGA_instruction_list.txt" % scan_name
    output_file = "%s/concecutive_tiggers/%s_concecutive_triggers.dat" % (obj.data_folder, timestamp)
    if not os.path.exists(os.path.dirname(output_file)):
        try:
            os.makedirs(os.path.dirname(output_file))
        except OSError as exc:  # Guard against race condition
            print "Unable to create directory"
    open(output_file, 'w').close()

    instruction_text = []
    instruction_text.append("1 Send RunMode")
    instruction_text.append("10 Send EC0")
    instruction_text.append("10 Send BC0")
    instruction_text.append("100 Send_Repeat LV1A 4000 100")
    instruction_text.append("1000 Send ReSync")

    # Write the instructions to the file.
    output_file_name = "./routines/%s/instruction_list.txt" % scan_name
    with open(output_file_name, "w") as mfile:
        for item in instruction_text:
            mfile.write("%s\n" % item)
    # Generate the instruction list for the FPGA.
    generator("Consecutive Triggers", obj.write_BCd_as_fillers, obj.register)


    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    obj.register[130].ECb[0] = 1
    obj.register[130].BCb[0] = 1
    obj.write_register(130)
    time.sleep(1)


    trigger_counter = 0
    data_packet_counter = 0
    hit_counter = 0
    crc_error_counter = 0
    ec_error_counter = 0
    bc_error_counter = 0
    start = time.time()



    for k in range(0, nr_loops):
        trigger_counter += 4000
        previous_EC = 0
        previous_BC = 0
        output = obj.interfaceFW.launch(obj.register, file_name, obj.COM_port, 1, save_data=1, obj=obj)
        if output[0] == "Error":
            text = "%s: %s\n" % (output[0], output[1])
            obj.add_to_interactive_screen(text)
        else:

            for i in output[3]:
                if i.type == "data_packet":
                    data_packet_counter += 1
                    if i.hit_found == 1:
                        hit_counter += 1
                    if i.crc_error == 1:
                        crc_error_counter += 1
                    ec_diff = i.EC - previous_EC
                    if ec_diff != 1:
                        print "->EC error"
                        print "Previous EC: %d" % previous_BC
                        print "Current EC: %d" % i.BC
                        ec_error_counter += 1
                    previous_EC = i.EC
                    bc_diff = i.BC - previous_BC
                    if bc_diff != 100:
                        print "->BC error"
                        print "Previous BC: %d" % previous_BC
                        print "Current BC: %d" % i.BC
                        bc_error_counter += 1
                    previous_BC = i.BC

        stop = time.time()
        run_time = (stop - start) / 60
        result = []
        result.append("-> %d Triggers sent." % trigger_counter)
        result.append("%d Data packets received." % data_packet_counter)
        result.append("CRC errors: %d" % crc_error_counter)
        result.append("EC errors: %d" % ec_error_counter)
        result.append("BC errors: %d" % bc_error_counter)
        result.append("Hits found: %d" % hit_counter)
        result.append("Time elapsed: %f min" % run_time)
        result.append("***************")

        with open(output_file, "a") as myfile:
            for line in result:
                print line
                myfile.write("%s\n" % line)

    obj.register[65535].RUN[0] = 0
    obj.write_register(65535)
    time.sleep(1)

    obj.register[130].ECb[0] = 0
    obj.register[130].BCb[0] = 0
    obj.write_register(130)
    time.sleep(1)
