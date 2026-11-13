# source me before building
export PATH=/opt/node22/bin:/usr/local/go/bin:/root/.cargo/bin:$PATH
NP=$(echo "$NO_PROXY" | sed 's/,proxy.golang.org//'); export NO_PROXY="$NP" no_proxy="$NP"
cd /home/claude/work/sotn-ultimate
source .venv/bin/activate
export NODE=/opt/node22/bin/node   # psp_dub.py does os.path.exists(NODE): needs an absolute path
