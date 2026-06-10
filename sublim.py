#!/usr/bin/python
import PySide6.QtWidgets as qt
from PySide6.QtGui import QFont, QCloseEvent, QPainter, QPen, QColor, QPainterPath
from PySide6.QtWidgets import QGraphicsOpacityEffect
from PySide6.QtCore import QTimer, Slot, QPointF
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl

import sys
import re
import random
import os
import time
import datetime
import math

million = 1000000


class _SessionClosed(Exception):
    """Raised by _wait() when the window is closing, to unwind blocking call stacks."""
    pass


class SpiralWidget(qt.QWidget):
    """Rotating Archimedean spiral for hypnotic eye fixation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rotAngle = 0.0
        self.setMinimumSize(500, 500)
        self._spiralTimer = QTimer()
        self._spiralTimer.setInterval(16)  # ~60fps
        self._spiralTimer.timeout.connect(self._tick)

    def startSpinning(self):
        self._spiralTimer.start()

    def stopSpinning(self):
        self._spiralTimer.stop()

    def _tick(self):
        self.rotAngle += 0.013  # ~1 revolution per 7.5 seconds
        if self.rotAngle > 2 * math.pi:
            self.rotAngle -= 2 * math.pi
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(8, 8, 15))

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        maxR = min(w, h) / 2 - 2
        rMin  = 3.0
        turns = 3.5
        steps = 320
        b = math.log(maxR / rMin) / (turns * 2 * math.pi)

        # Three evenly-spaced arms, two colour streams each (steel-blue + mauve)
        numArms = 3
        streams = [
            # (edge_color,            centre_color,          alpha, angle_offset)
            (QColor(45,  60,  95),  QColor(150, 175, 215),  58,  0.00),  # steel blue
            (QColor(90,  55, 108),  QColor(180, 145, 198),  42,  0.22),  # mauve, slight offset
        ]

        for armIdx in range(numArms):
            baseAngle = armIdx * (2 * math.pi / numArms) + self.rotAngle

            for (edgeC, centreC, baseAlpha, offset) in streams:
                er, eg, eb = edgeC.red(),   edgeC.green(),   edgeC.blue()
                cr, cg, cb = centreC.red(), centreC.green(), centreC.blue()

                pts = []
                for i in range(steps + 1):
                    frac  = i / steps
                    theta = frac * turns * 2 * math.pi + baseAngle + offset
                    r     = rMin * math.exp(b * frac * turns * 2 * math.pi)
                    pts.append(QPointF(cx + r * math.cos(theta),
                                       cy + r * math.sin(theta)))

                for i in range(1, len(pts)):
                    frac  = i / steps          # 0 = centre, 1 = edge
                    rc    = int(cr + (er - cr) * frac)
                    gc    = int(cg + (eg - cg) * frac)
                    bc    = int(cb + (eb - cb) * frac)
                    alpha = int(baseAlpha * (1.0 - frac * 0.45))
                    pw    = 1.5 + (1.0 - frac ** 0.55) * maxR * 0.06
                    painter.setPen(QPen(QColor(rc, gc, bc, alpha), pw,
                                        Qt.PenStyle.SolidLine,
                                        Qt.PenCapStyle.RoundCap))
                    painter.drawLine(pts[i - 1], pts[i])

        # Central tunnel glow
        painter.setPen(Qt.PenStyle.NoPen)
        for radius, alpha in [(80, 5), (40, 14), (16, 42), (6, 105), (2.5, 210)]:
            painter.setBrush(QColor(210, 228, 255, alpha))
            painter.drawEllipse(QPointF(cx, cy), float(radius), float(radius))


class windowBase(qt.QWidget):
    def __init__(self, fpath:str, isRandom: str, isburst: str, darkTheme: bool = False, bgAudio: str = None, locked: bool = False):
        super().__init__()
        self.isRand = (isRandom == "random")
        self.isBurst = (isburst == "burst")
        self._locked = locked
        with open(fpath, 'r') as file:
            rawLines = file.readlines()

        # Message weighting: [N] prefix expands a line N times in the rotation
        self.lines = []
        weightPat = re.compile(r'^\[(\d+)\]\s*(.+)', re.DOTALL)
        for line in rawLines:
            m = weightPat.match(line)
            if m:
                count = int(m.group(1))
                text = m.group(2)
                self.lines.extend([text] * count)
            else:
                self.lines.append(line)

        self.cur = 0
        self.timeMs = 44 # adjust this if you want. 44 is at good timing tho. should be 34-50ms for it still to be subliminal

        self.startedTime = datetime.datetime.now()
        self.timeFile = open("./rectime.txt", "a")
        self.timeFile.write(self.startedTime.strftime("date %Y-%m-%d %I:%M:%S %p\n"))

        # Background audio (looping entrainment track)
        self.bgSound = None
        if bgAudio:
            self.bgSound = QSoundEffect()
            self.bgSound.setSource(QUrl.fromLocalFile(bgAudio))
            self.bgSound.setLoopCount(-2)  # QSoundEffect.Infinite
            self.bgSound.setVolume(0.5)
            self.bgSound.play()

        self.tm = QTimer()
        self.tm.setInterval(self.timeMs)

        self.tm.timeout.connect(self.changeText)

        self.layout = qt.QGridLayout()
        self.setLayout(self.layout)


        self.text = qt.QLabel()
        self.text.setAlignment(Qt.AlignHCenter)
        self.font  = QFont("Arial", 60)
        self.text.setFont(self.font)

        self.layout.addWidget(self.text,0,0)
        self.setMinimumSize(1600, 100)
        self.adjustSize()

        if darkTheme:
            self.setStyleSheet("background-color: #0a0a0a; color: #f5e6c8;")

        self._closing = False
        self._sessionDone = False
        self.tm.start()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.show()


    def closeEvent(self, event: QCloseEvent):
        if self._locked and not self._sessionDone:
            event.ignore()
            return
        self._closing = True
        self.tm.stop()
        if self.bgSound is not None:
            self.bgSound.stop()
        delta = datetime.datetime.now() - self.startedTime
        seconds = delta.total_seconds()
        self.timeFile.write(str(seconds) + " seconds\n")
        self.timeFile.close()
        event.accept()

    def keyPressEvent(self, event):
        if self._locked:
            return  # swallow all keypresses
        super().keyPressEvent(event)

    def _wait(self, ms: int):
        """Like QTest.qWait but raises _SessionClosed if the window is closing."""
        if ms > 0:
            QTest.qWait(ms)
        if self._closing:
            raise _SessionClosed()

    def _fadeShowText(self, msg: str, holdMs: int, style: str = "", fadeInMs: int = 300, fadeOutMs: int = 300):
        """Fade text in, hold, fade out. Uses QGraphicsOpacityEffect + QTest.qWait."""
        steps = 12
        effect = QGraphicsOpacityEffect()
        self.text.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        self.text.setStyleSheet(style)
        self.text.setText(msg)
        for i in range(steps + 1):
            effect.setOpacity(i / steps)
            self._wait(max(1, fadeInMs // steps))
        self._wait(holdMs)
        for i in range(steps, -1, -1):
            effect.setOpacity(i / steps)
            self._wait(max(1, fadeOutMs // steps))
        self.text.setText("")
        self.text.setGraphicsEffect(None)

    def breathingGuide(self, totalMs: int, flashMsg: str = None):
        elapsed = 0
        while elapsed < totalMs:
            remaining = totalMs - elapsed
            inMs = min(4000, remaining)
            self.text.setStyleSheet("color: #7ec8e3;")
            self.text.setText("breathe in...")
            self._wait(inMs)
            elapsed += inMs
            if elapsed >= totalMs:
                break
            holdMs = min(4000, totalMs - elapsed)
            self.text.setStyleSheet("color: #b8a9c9;")
            self.text.setText("hold.")
            self._wait(holdMs)
            elapsed += holdMs
            if elapsed >= totalMs:
                break
            outMs = min(6000, totalMs - elapsed)
            self.text.setStyleSheet("color: #a8c5a0;")
            self.text.setText("breathe out...")
            if flashMsg and outMs >= 3000:
                # Flash suggestion at the relaxation peak of the exhale
                self._wait(2800)
                self.text.setStyleSheet("color: #f5e6c8;")
                self.text.setText(flashMsg.strip())
                self._wait(min(self.timeMs * 8, outMs - 2800))
                self.text.setStyleSheet("color: #a8c5a0;")
                self.text.setText("breathe out...")
                self._wait(max(0, outMs - 2800 - min(self.timeMs * 8, outMs - 2800)))
            else:
                self._wait(outMs)
            elapsed += outMs
        self.text.setStyleSheet("")
        self.text.setText("")


class window(windowBase):
    def __init__(self, fpath:str, isRandom: str, isburst: str, bgAudio: str = None):
        super().__init__(fpath, isRandom, isburst, bgAudio=bgAudio)
        self.burstWaitMin = 3000
        self.burstWaitMax = 5500

    @Slot()
    def changeText(self):
        try:
            if self.isRand:
                self.text.setText(self.lines[random.randrange(0, len(self.lines))])
            else:
                self.text.setText(self.lines[self.cur % len(self.lines)])

            if self.isBurst and (self.cur % len(self.lines) == 0):
                self._wait(self.timeMs)
                self.text.setText("")
                self._wait(random.randrange(self.burstWaitMin, self.burstWaitMax))

            self.cur += 1
        except _SessionClosed:
            pass


class consiousReinforcement(windowBase):
    def __init__(self, fpath:str, isRandom: str, isburst: str, bgAudio: str = None):
        super().__init__(fpath, isRandom, isburst, bgAudio=bgAudio)

        self.readable = False
        self.burstWaitMin = 3000
        self.burstWaitMax = 5500
        self.readableWait = 2500
        self.oneInProb = 55.0

        self.minSl = 40
        self.shownMsgsSl = 0

    @Slot()
    def changeText(self):
        rgot = random.randrange(0, million)

        if rgot < million / self.oneInProb and self.shownMsgsSl  > self.minSl:
            self.readable=True

        if self.isRand:
            self.text.setText(self.lines[random.randrange(0, len(self.lines))])
        else:
            self.text.setText(self.lines[self.cur % len(self.lines)])
        self.shownMsgsSl += 1
        try:
            if self.readable:
                self._wait(self.readableWait)
                self.readable=False
                self.shownMsgsSl = 0 # reset
            if self.isBurst and (self.cur % len(self.lines) == 0):
                self._wait(self.timeMs)
                self.text.setText("")
                self._wait(random.randrange(self.burstWaitMin,self.burstWaitMax))

            self.cur += 1
        except _SessionClosed:
            pass




class surpriser(windowBase):
    def __init__(self, fpath:str, isRandom: str, isburst: str, bgAudio: str = None):
        super().__init__(fpath, isRandom, isburst, bgAudio=bgAudio)
        self.burstWaitMin = 4000
        self.burstWaitMax = 35000
        self.randMsgWaitMin = 5000
        self.randMsgWaitMax = 10000
        self.oneInProb = 4.5

    @Slot()
    def changeText(self):
        if self.isRand:
            self.text.setText(self.lines[random.randrange(0, len(self.lines))])
        else:
            self.text.setText(self.lines[self.cur % len(self.lines)])

        try:
            rnd = random.randrange(0,million)
            if self.isBurst and (self.cur % len(self.lines) == 0):
                self._wait(self.timeMs)
                self.text.setText("")
                if rnd < million / self.oneInProb:
                    self._wait(random.randrange(self.randMsgWaitMin,self.randMsgWaitMax))
                    self.text.setText(self.lines[random.randrange(0, len(self.lines))])
                    self._wait(self.timeMs)
                    self.text.setText("")
                self._wait(random.randrange(self.burstWaitMin,self.burstWaitMax))

            self.cur += 1
        except _SessionClosed:
            pass


class surpriserBird(windowBase):
    def __init__(self, fpath:str, isRandom: str, isburst: str, bgAudio: str = None):
        super().__init__(fpath, isRandom, isburst, bgAudio=bgAudio)

        self.burstsWithoutBirds = 0
        self.burstWithoutMax = 8.0
        self.oneInProb = 5.3

        self.burstWaitMin = 6000
        self.burstWaitMax = 20000
        self.randMsgWaitMin = 5000
        self.randMsgWaitMax = 10000
        self.soundRandMsgDelay = 100

        birdPaths = ["./bird1.wav","./bird2.wav", "./bird3.wav", "./bird4.wav"]
        self.sounds = [QSoundEffect(),QSoundEffect(),QSoundEffect(),QSoundEffect()]
        i = 0
        for p in birdPaths:
            self.sounds[i].setSource(QUrl.fromLocalFile(p))
            self.sounds[i].setVolume(0.8)
            i += 1


    @Slot()
    def changeText(self):
        if self.isRand:
            self.text.setText(self.lines[random.randrange(0, len(self.lines))])
        else:
            self.text.setText(self.lines[self.cur % len(self.lines)])

        try:
            rnd = random.randrange(0,million)
            if self.isBurst and (self.cur % len(self.lines) == 0):
                self._wait(self.timeMs)
                self.text.setText("")

                if self.burstsWithoutBirds >= self.burstWithoutMax: # been damn long enough just play one now
                    self.playOneShowOne()
                elif rnd < million / self.oneInProb:
                    self.playOneShowOne()
                else:
                    self.burstsWithoutBirds += 1
                self._wait(random.randrange(self.burstWaitMin,self.burstWaitMax))

            self.cur += 1
        except _SessionClosed:
            pass

    def playOneShowOne(self):
        self._wait(random.randrange(self.randMsgWaitMin,self.randMsgWaitMax))
        random.choice(self.sounds).play()
        self._wait(self.soundRandMsgDelay)
        self.text.setText(self.lines[random.randrange(0, len(self.lines))])
        self._wait(self.timeMs)
        self.text.setText("")


class hypnoSession(windowBase):
    def __init__(self, fpath: str, durationMinutes: int, inductionFpath: str = None, bgAudio: str = None):
        super().__init__(fpath, "random", "burst", darkTheme=True, bgAudio=bgAudio)

        totalSecs = durationMinutes * 60
        self.inductionEnd = totalSecs * 0.15
        self.deepeningEnd = totalSecs * 0.25
        self.deliveryEnd  = totalSecs * 0.90

        self.inductionMs  = 500
        self.subliminalMs = 44

        self.burstWaitMin = 5000
        self.burstWaitMax = 18000

        self.deepeners = [
            "deeper now...",
            "that's right",
            "let it in",
            "sinking deeper...",
            "receive...",
            "open...",
            "yes...",
            "deeper...",
            "surrender...",
            "let go...",
        ]

        # Load separate induction script if provided
        if inductionFpath:
            with open(inductionFpath, 'r') as f:
                self.inductionLines = [l.strip() for l in f.readlines() if l.strip()]
        else:
            self.inductionLines = None  # falls back to main lines

        # Separate [emerge] tagged lines from delivery lines
        emerge = [l for l in self.lines if l.strip().lower().startswith('[emerge]')]
        self.lines = [l for l in self.lines if not l.strip().lower().startswith('[emerge]')]
        self.emergeLines = [l.strip()[len('[emerge]'):].strip() for l in emerge]
        if not self.emergeLines:
            self.emergeLines = [
                "returning now...",
                "gently waking...",
                "feeling refreshed...",
                "fully present...",
                "wide awake and clear...",
            ]

        self._emerged = False

        # Stop timer, rearrange layout: spiral on top, text below
        self.tm.stop()
        self.layout.removeWidget(self.text)
        self.spiral = SpiralWidget()
        self.layout.addWidget(self.spiral, 0, 0)
        self.layout.addWidget(self.text, 1, 0)
        self.setMinimumSize(550, 620)
        self.adjustSize()
        self.spiral.startSpinning()

        # Run body-scan relaxation before induction begins
        try:
            self._progressiveRelaxation()
        except _SessionClosed:
            return

        # Start timer at slow induction speed
        self.timeMs = self.inductionMs
        self.tm.setInterval(self.timeMs)
        self.tm.start()

    def _progressiveRelaxation(self):
        """Synchronous body-scan before induction: 10 cues + 2 breath cycles."""
        self.text.setFont(QFont("Arial", 36))
        sequence = [
            ("find a comfortable position...", 3500),
            ("soften your gaze on the spiral...", 4000),
            ("relax your forehead...", 3000),
            ("unclench your jaw...", 3000),
            ("drop your shoulders...", 3000),
            ("let your hands rest open...", 3000),
            ("breathe naturally...", 3000),
            ("you are safe here...", 3500),
            ("let your thoughts drift past...", 4000),
            ("becoming more receptive...", 4000),
        ]
        for msg, hold in sequence:
            self._fadeShowText(msg, hold, style="color: #f5e6c8;", fadeInMs=500, fadeOutMs=500)
        self.breathingGuide(28000)
        self.text.setFont(self.font)

    @Slot()
    def changeText(self):
        try:
            elapsed = (datetime.datetime.now() - self.startedTime).total_seconds()

            if elapsed < self.inductionEnd:
                self._runInduction()
            elif elapsed < self.deepeningEnd:
                self._runDeepening()
            elif elapsed < self.deliveryEnd:
                self._runDelivery()
            elif not self._emerged:
                self._runEmergence()
        except _SessionClosed:
            pass

    def _inductionMsg(self):
        pool = self.inductionLines if self.inductionLines else self.lines
        return random.choice(pool).strip()

    def _runInduction(self):
        msg = self._inductionMsg()
        self._fadeShowText(msg, 2000, style="color: #f5e6c8;", fadeInMs=500, fadeOutMs=500)
        self.breathingGuide(random.randrange(8000, 14000))

    def _runDeepening(self):
        elapsed = (datetime.datetime.now() - self.startedTime).total_seconds()
        deepeningDuration = self.deepeningEnd - self.inductionEnd
        progress = min(1.0, (elapsed - self.inductionEnd) / deepeningDuration)
        currentMs = int(self.inductionMs + (self.subliminalMs - self.inductionMs) * progress)
        if self.timeMs != currentMs:
            self.timeMs = currentMs
            self.tm.setInterval(self.timeMs)
        self.text.setStyleSheet("color: #f5e6c8;")
        self.text.setText(self.lines[random.randrange(len(self.lines))].strip())

    def _runDelivery(self):
        if self.timeMs != self.subliminalMs:
            self.timeMs = self.subliminalMs
            self.tm.setInterval(self.timeMs)
            self.spiral.hide()
        self.text.setStyleSheet("")
        self.text.setText(self.lines[random.randrange(len(self.lines))])
        if self.cur % len(self.lines) == 0:
            self._wait(self.timeMs)
            self.text.setText("")
            gapMs = random.randrange(self.burstWaitMin, self.burstWaitMax)
            rnd = random.randrange(0, million)
            if rnd < million / 4.5:
                # Breath-synced: flash a suggestion at exhale peak
                flashMsg = self.lines[random.randrange(len(self.lines))].strip()
                self.breathingGuide(gapMs, flashMsg=flashMsg)
            elif rnd < million / 2.5:
                # Deepener phrase mid-gap
                deepener = random.choice(self.deepeners)
                self._wait(random.randrange(1500, 4000))
                self._fadeShowText(deepener, 2000, style="color: #c8b8d8;", fadeInMs=300, fadeOutMs=500)
                self._wait(max(0, gapMs - 7500))
            else:
                self._wait(gapMs)
        self.cur += 1

    def _runEmergence(self):
        self._emerged = True
        self.tm.stop()
        self.spiral.show()

        # Ramp flash speed from subliminal back to readable
        rampSteps = 20
        for i in range(rampSteps):
            t = int(self.subliminalMs + (400 - self.subliminalMs) * (i / rampSteps))
            self.text.setStyleSheet("color: #f5e6c8;")
            self.text.setText(self.lines[random.randrange(len(self.lines))].strip())
            self._wait(t)

        self.text.setText("")
        self.breathingGuide(14000)

        for msg in self.emergeLines:
            self._fadeShowText(msg, 2500, style="color: #f5e6c8;", fadeInMs=600, fadeOutMs=600)
            self._wait(500)

        self.breathingGuide(14000)

        self._fadeShowText("awaken.", 4000, style="color: #f5e6c8;", fadeInMs=800, fadeOutMs=800)
        self._sessionDone = True
        self.close()


if __name__=="__main__":
    import signal
    app=qt.QApplication()

    # Parse locked flag
    locked = "lock" in sys.argv
    if locked:
        sys.argv = [a for a in sys.argv if a != "lock"]
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # ignore Ctrl+C
    else:
        signal.signal(signal.SIGINT, lambda *_: app.quit())

    # Parse bg audio flag: `bg ./file.wav` can appear anywhere after the file path arg
    bgAudio = None
    rawArgs = sys.argv[2:]
    cleanArgs = []
    i = 0
    while i < len(rawArgs):
        if rawArgs[i] == "bg" and i + 1 < len(rawArgs):
            bgAudio = rawArgs[i + 1]
            i += 2
        else:
            cleanArgs.append(rawArgs[i])
            i += 1

    mode = cleanArgs[0] if cleanArgs else None

    # Parse induction file flag
    inductionFpath = None
    filteredArgs = []
    i = 0
    while i < len(cleanArgs):
        if cleanArgs[i] == "induction" and i + 1 < len(cleanArgs):
            inductionFpath = cleanArgs[i + 1]
            i += 2
        else:
            filteredArgs.append(cleanArgs[i])
            i += 1
    cleanArgs = filteredArgs
    mode = cleanArgs[0] if cleanArgs else None

    if len(sys.argv) >= 2:
        if mode == "rb":
            win=window(sys.argv[1], "random", "burst", bgAudio=bgAudio)
        elif mode == "b":
            win=window(sys.argv[1], "", "burst", bgAudio=bgAudio)
        elif mode == "r":
            win=window(sys.argv[1], "random", "", bgAudio=bgAudio)
        elif mode == "c":
            win=consiousReinforcement(sys.argv[1], "random", "burst", bgAudio=bgAudio)
        elif mode == "s":
            win=surpriser(sys.argv[1], "random", "burst", bgAudio=bgAudio)
        elif mode == "bird":
            win=surpriserBird(sys.argv[1], "random", "burst", bgAudio=bgAudio)
        elif mode == "hypno":
            durationMinutes = int(cleanArgs[1]) if len(cleanArgs) > 1 else 20
            win=hypnoSession(sys.argv[1], durationMinutes, inductionFpath=inductionFpath, bgAudio=bgAudio)
        elif mode is None:
            win=window(sys.argv[1], "", "", bgAudio=bgAudio)
        else:
            print("USAGE: python ./sublim.py [text file] [r|b|rb|c|s|bird|hypno [minutes]] [bg ./audio.wav] [induction ./script.txt]")
            quit()
    else:
        print("USAGE: python ./sublim.py [text file] [r|b|rb|c|s|bird|hypno [minutes]] [bg ./audio.wav] [induction ./script.txt]")
        quit()

    app.exec()
