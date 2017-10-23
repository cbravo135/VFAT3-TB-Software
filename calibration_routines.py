from routines import *
from generator import *
import ROOT as r
import numpy as np


def cal_dac_steps(obj):

    start_dac_value = 0
    stop_dac_value = 255

    obj.register[133].Monitor_Sel[0] = 33
    obj.write_register(133)

    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(0.1)

    step_values = []
    dac_values = []
    charge_values = []

    obj.register[138].CAL_SEL_POL[0] = 1
    obj.write_register(138)
    time.sleep(0.1)

    baseADC = obj.read_adc0()
    base = obj.adc0M * baseADC + obj.adc0B

    obj.register[138].CAL_SEL_POL[0] = 0
    obj.write_register(138)
    time.sleep(0.1)

    for i in range(0, 255, 5):
        #newVal = raw_input("ready?")
        obj.register[138].CAL_DAC[0] = i
        obj.write_register(138)

        stepADC = obj.read_adc0()
        step = obj.adc0M*stepADC + obj.adc0B

        difference = step-base
        charge = (difference/1000.0) * 100.0  # 100 fF capacitor.

        step_values.append(step)
        dac_values.append(float(255-i))
        charge_values.append(charge)

        print "DAC value: %d" % i
        print "Base value: %f mV, step value: %f mV" % (base, step)
        print "Difference: %f mV, CHARGE: %f fC" % (difference, charge)
        print "--------------------------------"

    obj.cal_dac_fc_values = charge_values

    return dac_values, base, step_values, charge_values


def scan_cal_dac_fc(obj, scan_name):
    if obj.adc0M == 0 or obj.adc0B == 0 or obj.adc1M == 0 or obj.adc1B == 0:
        text = "\nADCs are not calibrated. Run ADC calibration first.\n"
        obj.add_to_interactive_screen(text)
    else:
        start = time.time()
        modified = scan_name.replace(" ", "_")
        modified = modified.replace(",", "_")

        dac_values, base_value, step_values, charge_values = cal_dac_steps(obj)

        calc_cal_dac_conversion_factor(obj, dac_values, charge_values)

        # data = [dac_values, charge_values]
        # timestamp = time.strftime("%Y%m%d%H%M")
        # folder = "./results/"
        # filename = "%s%s_%s_scan_data.dat" % (folder, timestamp, modified)
        #
        # outF = open(filename, "w")
        # outF.write("dacValue/D:baseV/D:stepV/D:Q/D\n")
        # for i,dacVal in enumerate(dac_values):
        #     outF.write('%f\t%f\t%f\t%f\n'%(dacVal,base_values[i],step_values[i],charge_values[i]))
        #     pass
        # outF.close()
        # text = "\nResults were saved to the file:\n %s \n" % filename
        #
        # obj.add_to_interactive_screen(text)

        stop = time.time()
        run_time = (stop - start) / 60
        text = "\nScan duration: %f min\n" % run_time
        obj.add_to_interactive_screen(text)


def calc_cal_dac_conversion_factor(obj, dac_values, charge_values):

    r.gStyle.SetStatX(0.5)
    r.gStyle.SetStatY(0.8)
    r.gStyle.SetOptFit(True)

    cal_dac_fc_g = r.TGraph(len(dac_values), np.array(dac_values), np.array(charge_values))

    cal_dac_fc_g.SetName('cal_dac_fc_g')
    cal_dac_fc_g.SetTitle('CAL_DAC Calibration;255-CAL_DAC;Charge [fC]')
    cal_dac_fc_g.SetMarkerStyle(3)

    cal_dac_fc_fitR = cal_dac_fc_g.Fit('pol1','S')

    obj.cal_dac_fcM = cal_dac_fc_fitR.GetParams()[1]
    obj.cal_dac_fcB = cal_dac_fc_fitR.GetParams()[0]

    canv = r.TCanvas('canv','canv', 1000, 1000)
    canv.cd()

    cal_dac_fc_g.Draw('ap')
    canv.SaveAs('%s/cal_dac_fc.png'%obj.data_folder)

    text = "\nCAL_DAC conversion completed.\n"
    text += "CAL_DAC to fC: %f + %f\n" % (obj.cal_dac_fcM, obj.cal_dac_fcB)
    obj.add_to_interactive_screen(text)


def iref_adjust(obj):

    # Read the current Iref dac value.
    obj.read_register(134)
    obj.register[134].Iref[0] = 10
    obj.write_register(134)
    previous_value = 10

    # Set monitoring to Iref
    obj.register[133].Monitor_Sel[0] = 0
    obj.write_register(133)

    # Set RUN bit to activate analog part.
    obj.register[65535].RUN[0] = 1
    obj.write_register(65535)
    time.sleep(1)

    previous_diff = 1000
    text = "\nAdjusting the global reference current.\n"
    print text
    obj.add_to_interactive_screen(text)
    obj.interfaceFW.start_ext_adc()
    while True:

        time.sleep(0.1)
        output = obj.interfaceFW.ext_adc()
        if output == "Error":
            print "No response from ADC, aborting Iref adjustment."
            break
        print "Iref: %f, target: 100 mV. DAC: %d" % (output, obj.register[134].Iref[0])
        new_diff = abs(100 - output)

        if previous_diff < new_diff:
            print "->Difference increasing. Choose previous value: %d." % previous_value
            obj.register[134].Iref[0] = previous_value
            obj.Iref = previous_value
            obj.write_register(134)
            break
        previous_value = obj.register[134].Iref[0]
        if output < 100:
            print "->Value too low, increase Iref register by 1."
            obj.register[134].Iref[0] += 1
        else:
            print "->Value too high, decrease Iref register by 1."
            obj.register[134].Iref[0] -= 1
        obj.write_register(134)
        previous_diff = new_diff

    obj.interfaceFW.stop_ext_adc()
    obj.register[65535].RUN[0] = 0
    obj.write_register(65535)
    time.sleep(1)
    text = "- Iref adjusted.\n"
    obj.Iref_cal = 1
    print text
    obj.add_to_interactive_screen(text)


def adc_calibration(obj):

    if obj.Iref_cal == 0:
        text = "\nIref is not calibrated. Run Iref calibration first.\n"
        obj.add_to_interactive_screen(text)
    else:
        obj.register[133].Monitor_Sel[0] = 2
        obj.write_register(133)

        obj.register[65535].RUN[0] = 1
        obj.write_register(65535)
        time.sleep(1)

        int_adc0_values = []
        int_adc1_values = []
        ext_adc_values = []
        dac_values = []
        obj.interfaceFW.start_ext_adc()
        for i in range(0, 252, 10):
            value = i
            dac_values.append(value)
            print "->Measuring DAC value %d" % value
            obj.register[141].PRE_I_BIT[0] = value
            obj.write_register(141)
            time.sleep(0.1)
            int_adc0_value = float(obj.read_adc0())
            print int_adc0_value
            int_adc0_values.append(int_adc0_value)

            int_adc1_value = float(obj.read_adc1())
            int_adc1_values.append(int_adc1_value)

            ext_adc_value = obj.interfaceFW.ext_adc()

            print "ext. ADC: %f" % ext_adc_value
            ext_adc_values.append(ext_adc_value)

        obj.interfaceFW.stop_ext_adc()
        obj.register[133].Monitor_Sel[0] = 0
        obj.write_register(133)

        obj.register[65535].RUN[0] = 0
        obj.write_register(65535)
        time.sleep(1)

        calc_adc_conversion_constants(obj, ext_adc_values, int_adc0_values, int_adc1_values)

        adc0_values_conv = []
        for item in int_adc0_values:
            adc0_values_conv.append(item*obj.adc0M+obj.adc0B)

        adc1_values_conv = []
        for item in int_adc1_values:
            adc1_values_conv.append(item*obj.adc1M+obj.adc1B)

        text = "\nInternal ADCs calibrated. Values:\n"
        text += "ADC0: %f + %f\n" % (obj.adc0M, obj.adc0B)
        text += "ADC1: %f + %f\n" % (obj.adc1M, obj.adc1B)
        obj.add_to_interactive_screen(text)


def calc_adc_conversion_constants(obj, ext_adc, int_adc0, int_adc1):

    r.gStyle.SetStatX(0.5)
    r.gStyle.SetStatY(0.8)
    r.gStyle.SetOptFit(True)

    adc0_Conv_g = r.TGraph(len(ext_adc), np.array(int_adc0), np.array(ext_adc))
    adc1_Conv_g = r.TGraph(len(ext_adc), np.array(int_adc1), np.array(ext_adc))

    adc0_Conv_g.SetName('adc0_Conv_g')
    adc1_Conv_g.SetName('adc1_Conv_g')
    adc0_Conv_g.SetTitle('ADC0 Calibration;ADC0;Vmean [mV]')
    adc1_Conv_g.SetTitle('ADC1 Calibration;ADC1;Vmean [mV]')
    adc0_Conv_g.SetMarkerStyle(3)
    adc1_Conv_g.SetMarkerStyle(3)

    adc0fitR = adc0_Conv_g.Fit('pol1', 'S')
    adc1fitR = adc1_Conv_g.Fit('pol1', 'S')

    obj.adc0M = adc0fitR.GetParams()[1]
    obj.adc0B = adc0fitR.GetParams()[0]

    obj.adc1M = adc1fitR.GetParams()[1]
    obj.adc1B = adc1fitR.GetParams()[0]

    canv = r.TCanvas('canv', 'canv', 1000, 1000)
    canv.cd()

    adc1_Conv_g.Draw('ap')
    canv.SaveAs('%s/adc1_cal.png'%obj.data_folder)

    adc0_Conv_g.Draw('ap')
    canv.SaveAs('%s/adc0_cal.png'%obj.data_folder)


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
        output = scurve_all_ch_execute(obj, "S-curve all ch", arm_dac=100, ch=[k, k], configuration="no")
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

            output = scurve_all_ch_execute(obj, "S-curve all ch", arm_dac=100, ch=[k, k], configuration="no")
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


def gain_measurement(obj):

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
        # extADC.append(0)
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
        outF.write('%i\t%i\t%i\t%i\t%f\n' % (armdac, ADC0[i], ADC1[i], extADC[i], threshold_fc[i]))
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
