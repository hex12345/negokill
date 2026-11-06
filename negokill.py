import os, sys, time, random, signal, select

REAL = "/bin/kill"
R, Y, D, X = "\033[91m", "\033[93m", "\033[2m", "\033[0m"
NINE = ("-9", "-KILL", "-SIGKILL", "-s9")

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

def child_count(target_pid):
    count = 0
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            try:
                with open(f"/proc/{entry}/stat") as f:
                    ppid = f.read().rsplit(")", 1)[1].split()[1]
                    if int(ppid) == int(target_pid):
                        count += 1
            except (OSError, IndexError, ValueError):
                continue
    return count

def talk(who, line, col=Y, out=sys.stdout):
    out.write(f"{col}[{who}] ")
    for c in line:
        out.write(c); out.flush(); time.sleep(0.015)
    out.write(X + "\n"); out.flush()

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

def pick_offer(pid):
    c = child_count(pid)
    offers = OFFERS if c > 0 else [o for o in OFFERS if "{c}" not in o]
    return random.choice(offers).format(m=max(rss_mb(pid), 1), c=c)


# negotiation happens on the sender side, so it works for any process and for -9
def wrapper(args):
    pids = [a for a in args if a.isdigit()]
    if not pids:
        os.execv(REAL, [REAL] + args)
    nine = any(a in NINE for a in args)
    approved = []
    for p in pids:
        n = name_of(p)
        if not n:
            approved.append(p); continue
        talk(n, pick_offer(p))
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
            talk(n, random.choice(LAST_WORDS).format(p=p), D)
            time.sleep(1)
        else:
            talk(n, random.choice(["fine. FINE. i'll go quietly. SIGTERM accepted.", "you'll be hearing from my parent process."]))
        approved.append(p)
    if not approved:
        return 1
    flags = [a for a in args if not a.isdigit()]
    os.execv(REAL, [REAL] + flags + approved)

# hostage mode (by @jerryjhird): this process itself negotiates when sigterm'd.
# it freezes the sender's shell and talks through the sender's own terminal.
# SIGKILL can't be caught, so -9 negotiation stays in the wrapper.
def hostage(timeout=30):
    pid = os.getpid()
    name = "hostage"
    sigset = {signal.SIGTERM, signal.SIGINT}
    # block before announcing the pid, otherwise an early kill skips the negotiation
    signal.pthread_sigmask(signal.SIG_BLOCK, sigset)

    print("listening for sigterm...")
    print(f"in a separate shell run: {R}kill {pid}{X}  (kill must be a shell builtin, check: type kill)")

    while True:
        info = signal.sigwaitinfo(sigset)
        sender = info.si_pid
        # si_pid is 0 for kernel-generated signals like Ctrl+C on the tty;
        # os.kill(0, SIGSTOP) would freeze our own process group
        if sender <= 0:
            print(f"\n{D}[{name}:{pid}] ctrl+c? no negotiation then. goodbye.{X}")
            sys.exit(0)

        stopped = False
        try:
            out = open(f"/proc/{sender}/fd/1", "w")
            inp = open(f"/proc/{sender}/fd/0", "r")
        except OSError as e:
            print(f"{D}[{name}:{pid}] couldn't reach pid {sender}'s terminal ({e}). dying quietly.{X}")
            sys.exit(0)

        try:
            # only negotiate with a human: if the sender's stdin isn't a tty
            #
            if not os.isatty(inp.fileno()):
                print(f"{D}[{name}:{pid}] killed by a non-interactive sender ({name_of(sender)}). no deal.{X}")
                sys.exit(0)

            try:
                os.kill(sender, signal.SIGSTOP)
                stopped = True
            except OSError:
                pass

            talk(f"{name}:{pid}", pick_offer(pid), out=out)
            out.write(f"{R}> accept the deal? (y/n) [{timeout}s]: {X}"); out.flush()

            ready, _, _ = select.select([inp], [], [], timeout)
            ans = inp.readline().strip().lower() if ready else ""
            if not ready:
                out.write("\n")

            if ans.startswith("y"):
                talk(f"{name}:{pid}", "THANK YOU. surviving!", out=out)
                continue
            talk(f"{name}:{pid}", random.choice(LAST_WORDS).format(p=pid), D, out=out)
        except Exception as e:
            print(f"{D}[{name}:{pid}] negotiation failed: {e}{X}")
        finally:
            # always unfreeze the sender, even on errors
            if stopped:
                try:
                    os.kill(sender, signal.SIGCONT)
                except OSError:
                    pass
            out.close(); inp.close()

        print(f"{D}terminating...{X}")
        sys.exit(0)

if __name__ == "__main__":
    if sys.argv[1:2] == ["--hostage"]:
        hostage()
    else:
        sys.exit(wrapper(sys.argv[1:]))
