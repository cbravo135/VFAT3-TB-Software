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
