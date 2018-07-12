#define FLAG_PRESENT 0x3131

header_type flag_t {
  fields {
    f1 : 16;
    f2 : 64;
    f3 : 16;
    f4 : 16;
  }
}

header_type meta_t {
  fields {
    f1 : 16;
  }
}

header flag_t flag;
metadata meta_t meta;

parser start {
  return select(current(0, 16)) {
    FLAG_PRESENT : parse_flag;
    default : ingress;
  }
}

parser parse_flag {
  extract(flag);
  return ingress;
}

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

action add_flag(xorval1, xorval2) {
  add_header(flag);
  modify_field(flag.f1, FLAG_PRESENT);
  modify_field_rng_uniform(flag.f2, 0, 0xFFFFFFFFFFFFFFFF);
  bit_xor(meta.f1, flag.f1, xorval1);
  modify_field(flag.f3, meta.f1);
  bit_xor(flag.f4, flag.f3, xorval2);
}

action remove_flag() {
  remove_header(flag);
}

table is_flag_present {
  reads {
    flag : valid;
  }
  actions {
    add_flag;
    remove_flag;
  }
}

control ingress {
  apply(fwd);
  apply(is_flag_present);
}
