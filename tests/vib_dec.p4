#define VIBRANT_FLAG 0x020101010101

header_type vibrant_t {
  fields {
    flag : 48;
    hKeyIndex : 64; // choose 8
  }
}

header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}

header_type could_be_ipv4_t {
    fields {
        unused : 96;
        srcAddr : 32;
        dstAddr: 32;
    }
}

header_type intrinsic_metadata_t {
  fields {
        ingress_global_timestamp : 48;
        lf_field_list : 8;
        mcast_grp : 16;
        egress_rid : 16;
        resubmit_flag : 8;
        recirculate_flag : 8;
  }
}

header vibrant_t vibrant;
header ethernet_t ethernet;
header could_be_ipv4_t could_be_ipv4;

metadata intrinsic_metadata_t intrinsic_metadata;

parser start {
  extract(ethernet);
  extract(could_be_ipv4);
  return select(current(0, 48)) {
    VIBRANT_FLAG : parse_vibrant;
    default: ingress;
  }
}

parser parse_vibrant {
  extract(vibrant);
  return ingress;
}

action vibrant_present() { }
action vibrant_not_present() { }

table check_vibrant {
  reads {
    vibrant : valid;
  }
  actions {
    vibrant_present;
    vibrant_not_present;
  }
}

action a_decrypt(k1, k2, k3, k4) {
  bit_xor(ethernet.dstAddr, ethernet.dstAddr, k1);
  bit_xor(ethernet.srcAddr, ethernet.srcAddr, k2);
  bit_xor(could_be_ipv4.dstAddr, could_be_ipv4.dstAddr, k3);
  bit_xor(could_be_ipv4.srcAddr, could_be_ipv4.srcAddr, k4);
}

table decrypt {
  reads {
    vibrant.hKeyIndex : ternary;
  }
  actions {
    a_decrypt;
  }
}

action a_strip_vibrant() {
  remove_header(vibrant);
}

table strip_vibrant {
  actions {
    a_strip_vibrant;
  }
}

control ingress {
  apply(check_vibrant) {
    vibrant_present {
      apply(decrypt);
      apply(strip_vibrant);
    }
  }
}
