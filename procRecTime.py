#!/usr/bin/python


if __name__ == "__main__":
    lines = []
    with open("./rectime.txt", 'r') as file:
            lines = file.readlines()

    recs = []
    byDay = {}
    for i in range(0, len(lines)):
        if i % 2 == 1:
            recs.append((lines[i].split())[0])
        else:
            sp = lines[i].split()
            day = sp[1]

            secs = lines[i+1].split()[0]
            if not day in byDay:
                byDay[day] = 0.0
            byDay[day] += float(secs)


    total = 0.0
    for rec in recs:
        total += float(rec)

    print("total time by day:")

    for k in byDay:
        print(k, byDay[k])

    print("total time " + str(total) + " seconds")
