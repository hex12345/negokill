# negokill

`kill`, but the process negotiates for its life. `-9` summons a negotiator.

## wrapper mode (default)

any process you kill begs first.

```sh
curl -fsSL https://raw.githubusercontent.com/hex12345/negokill/master/negokill.py -o ~/negokill.py
echo "alias kill='python3 ~/negokill.py'" >> ~/.bashrc
```

escape hatch: `\kill`.

## hostage mode

a real process that negotiates when it gets sigterm'd. it freezes your shell and begs through your own terminal (by [@jerryjhird](https://github.com/jerryjhird)).

> [!IMPORTANT]
> `kill` must be a shell builtin for this one (check with `type kill`), and don't have the wrapper alias active in that shell (use `\kill`).

```sh
python3 ~/negokill.py --hostage
# in another shell:
\kill <pid>
```

have fun!
