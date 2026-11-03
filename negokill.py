import os, sys, time, random

REAL = "/bin/kill"
R, Y, D, X = "\033[91m", "\033[93m", "\033[2m", "\033[0m"

def name_of(pid):
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except OSError:
        return None

def rss_mb(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for l in f:
                if l.startswith("VmRSS"):
                    return int(l.split()[1]) // 1024
    except OSError:
        pass
    return 0

def talk(who, line, col=Y):
    sys.stdout.write(f"{col}[{who}] ")
    for c in line:
        sys.stdout.write(c); sys.stdout.flush(); time.sleep(0.015)
    print(X)

OFFERS = [
    "wait WAIT. i'll give you back {m}MB of RAM. just let me live.",
    "i have children. {c} child processes. who's going to reap them?!",
    "i'll stop using so much CPU. i swear. i'll be nice()d.",
    "i know where your swap file is. let's not make this ugly.",
    "please. i was just about to finish. 99%. ninety-nine percent.",
]
LAST_WORDS = [
    "tell my parent process... i was a good fork...",
    "remember me... by my PID... {p}...",
    "it's getting dark... is this... SIGKILL...",
    "i regret nothing. except that memory leak.",
]
NEGOTIATOR = "Hostage negotiator here. Nobody needs to get SIGKILLed today. Take a breath. Can we talk about this?"

def main():
    args = sys.argv[1:]
    pids = [a for a in args if a.isdigit()]
    if not pids:
        os.execv(REAL, [REAL] + args)
    nine = any(a in ("-9", "-KILL", "-SIGKILL", "-s9") for a in args)
    approved = []
    for p in pids:
        n = name_of(p)
        if not n:
            approved.append(p); continue
        children = len([c for c in os.listdir("/proc") if c.isdigit() and _ppid(c) == p])
        talk(n, random.choice(OFFERS).format(m=max(rss_mb(p), 1), c=children))
        if nine:
            talk("negotiator", NEGOTIATOR, D)
        try:
            ans = input(f"{R}> accept the deal? (y/n): {X}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(); talk(n, "...you hesitated. i knew you were a good person."); return 1
        if ans.startswith("y"):
            talk(n, "THANK YOU. you won't regret this. (you will.)")
            continue
        if nine:
            for lw in [random.choice(LAST_WORDS).format(p=p)]:
                talk(n, lw, D)
                time.sleep(1)
        else:
            talk(n, random.choice(["fine. FINE. i'll go quietly. SIGTERM accepted.", "you'll be hearing from my parent process."]))
        approved.append(p)
    if not approved:
        return 1
    flags = [a for a in args if not a.isdigit()]
    os.execv(REAL, [REAL] + flags + approved)

def _ppid(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[1]
    except (OSError, IndexError):
        return None

if __name__ == "__main__":
    sys.exit(main())
