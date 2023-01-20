#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

FROM ghcr.io/carbynestack/spdz:642d11f_no-offline

ADD run.sh .
RUN chmod +x run.sh
VOLUME ["/mp-spdz/Player-Data"]
VOLUME ["/mp-spdz/Programs/Source"]

CMD ["./run.sh"]
