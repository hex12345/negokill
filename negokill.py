import os, sys, time, random, signal

R, Y, D, X = "\033[91m", "\033[93m", "\033[2m", "\033[0m"

def name_of(pid):
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except OSError:
        return "unknown"

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
                    if int(ppid) == target_pid:
                        count += 1
            except (OSError, IndexError):
                continue
    return count

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

def main():
    pid = os.getpid()
    name = os.path.basename(sys.argv[0]) or "process"
    
    print(f"listening for sigterm...")
    print(f"in a seperate shell run: {R}kill {pid}{X}")

    sigset = {signal.SIGTERM, signal.SIGINT}
    signal.pthread_sigmask(signal.SIG_BLOCK, sigset)

    while True:
        info = signal.sigwaitinfo(sigset)
        sender_pid = info.si_pid
        sender_name = name_of(sender_pid)

        try:
            os.kill(sender_pid, signal.SIGSTOP)
        except OSError:
            pass

        try:
            with open(f"/proc/{sender_pid}/fd/1", "w") as out, open(f"/proc/{sender_pid}/fd/0", "r") as inp:
                children_c = child_count(pid)

                # remove offers that contain children count if children count is 0
                available_offers = list(OFFERS)
                if children_c <= 0:
                    available_offers = [o for o in available_offers if "{c}" not in o]

                offer = random.choice(available_offers).format(m=rss_mb(pid), c=children_c)
                out.write(f"\n{Y}[{name}:{pid}] " + offer + f"{X}\n")
                out.write(f"{R}> accept the deal? (y/n): {X}")
                out.flush()

                ans = inp.readline().strip().lower()

                # resume shell
                try:
                    os.kill(sender_pid, signal.SIGCONT)
                except OSError:
                    pass

                if ans.startswith("y"):
                    out.write(f"{Y}[{name}:{pid}] THANK YOU. Surviving!{X}\n")
                    out.flush()
                    continue
                
                out.write(f"{D}[{name}:{pid}] " + random.choice(LAST_WORDS).format(p=pid) + f"{X}\n")
                out.flush()
                time.sleep(1)
        except Exception as e:
            # unfreeze shell if error
            try:
                os.kill(sender_pid, signal.SIGCONT)
            except OSError:
                pass

        print(f"{D}terminating...{X}")
        sys.exit(0)

if __name__ == "__main__":
    main()
