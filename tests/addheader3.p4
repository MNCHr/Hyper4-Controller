#define FLAG_PRESENT 0x313131313131

header_type flag_t {
  fields {
    f1 : 48;
    f2 : 64;
    f3 : 16;
  }
}

header flag_t flag;

parser start {
  return select(current(0, 48)) {
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

action add_flag() {
  add_header(flag);
  modify_field(flag.f1, FLAG_PRESENT);
  modify_field_rng_uniform(flag.f2, 0, 0xFFFFFFFFFFFFFFFF);
  modify_field(flag.f3, 0xAABB);
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
