/*
Copyright 2013-present Barefoot Networks, Inc. 

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

#include "includes/headers.p4"
#include "includes/parser.p4"

field_list ipv4_csum {
  ipv4.version;
  ipv4.ihl;
  ipv4.diffserv;
  ipv4.totalLen;
  ipv4.identification;
  ipv4.flags;
  ipv4.fragOffset;
  ipv4.ttl;
  ipv4.protocol;
  ipv4.srcAddr;
  ipv4.dstAddr;
}

field_list_calculation ipv4_calc {
  input {
    ipv4_csum;
  }
  algorithm : csum16;
  output_width : 16;
}

calculated_field ipv4.hdrChecksum {
  update ipv4_calc;
}

header_type routing_metadata_t {
    fields {
        nhop_ipv4 : 32;
    }
}

metadata routing_metadata_t routing_metadata;

// 1
action is_valid() {
}

// 2
action is_not_valid() {
}

table is_ipv4_valid {
  reads {
    ipv4 : valid;
  }
  actions {
    is_valid;
    is_not_valid;
  }
}

// 3
action _drop() {
    drop();
}

// 4
action _no_op() {
}

// 5
action set_nhop(nhop_ipv4, port) {
    modify_field(routing_metadata.nhop_ipv4, nhop_ipv4);
    modify_field(standard_metadata.egress_spec, port);
    add_to_field(ipv4.ttl, -1);
}

table ipv4_lpm {
    reads {
        ipv4.dstAddr : exact;
    }
    actions {
        set_nhop;
        _drop;
        _no_op;
    }
    size: 1024;
}

// 6
action set_dmac(dmac) {
    modify_field(ethernet.dstAddr, dmac);
}

table forward {
    reads {
        routing_metadata.nhop_ipv4 : exact;
    }
    actions {
        set_dmac;
        _drop;
    }
    size: 512;
}

// 7
action rewrite_mac(smac) {
    modify_field(ethernet.srcAddr, smac);
}

table send_frame {
    reads {
        standard_metadata.egress_spec: exact;
    }
    actions {
        rewrite_mac;
        _drop;
    }
    size: 256;
}

control ingress {
  apply(is_ipv4_valid) {
    is_valid {
      apply(ipv4_lpm) {
        set_nhop {
          apply(forward);
          apply(send_frame);
        }
      }
    }
  }
}
