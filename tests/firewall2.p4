header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}

header_type ipv4_t {
    fields {
        version : 4;
        ihl : 4;
        diffserv : 8;
        totalLen : 16;
        identification : 16;
        flags : 3;
        fragOffset : 13;
        ttl : 8;
        protocol : 8;
        hdrChecksum : 16;
        src : 32;
        dst : 32;
    }
}

header_type l4_t {
    fields {
        src : 16;
        dst : 16;
    }
}

header ethernet_t ethernet;

parser start {
    extract(ethernet);
    return select(ethernet.etherType) {
      0x0800 : parse_ipv4;
      default : ingress;
    }
}

header ipv4_t ipv4;

parser parse_ipv4 {
  extract(ipv4);
  return select(ipv4.protocol) {
    0x06 : parse_l4; // tcp
    0x11 : parse_l4; // udp
    default : ingress;
  }
}

header l4_t l4;

parser parse_l4 {
  extract(l4);
  return ingress;
}

// action ID: 
action a_fwd(port) {
  modify_field(standard_metadata.egress_spec, port);
}

table fwd {
  reads {
    standard_metadata.ingress_port : exact;
  }
  actions {
    a_fwd;
  }
}

// action ID: 
action _no_op() {
}

// action ID: 
action l4_is_valid() {
}

table is_l4_valid {
  reads {
    l4 : valid;
  }
  actions {
    l4_is_valid;
    _no_op;
  }
}

action _drop() {
  drop();
}

table fw_src {
  reads {
    l4.src : exact;
  }
  actions {
    _drop;
    _no_op;
  }
}

table fw_dst {
  reads {
    l4.dst : exact;
  }
  actions {
    _drop;
    _no_op;
  }
}

control ingress {
  apply(fwd);
  apply(is_l4_valid) {
    l4_is_valid {
      apply(fw_src) {
        _no_op {
          apply(fw_dst);
        }
      }
    }
  }
}
