header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}

header_type intelem_t {
  fields {
    timestamp : 48;
    ingress_port : 16;
    saved_etherType : 16;
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

header ethernet_t ethernet;
header intelem_t intelem;
metadata intrinsic_metadata_t intrinsic_metadata;

parser start {
  extract(ethernet);
  return select(ethernet.etherType) {
      0x52dc : parse_intelem;
      default : ingress;
  }
}

parser parse_intelem {
  extract(intelem);
  return ingress;
}

action _drop() {
  drop();
}

action forward(port) {
  modify_field(standard_metadata.egress_spec, port);
}

action forward_int_eligible(port) {
  modify_field(standard_metadata.egress_spec, port);
}

action broadcast(mcast) {
  modify_field(intrinsic_metadata.mcast_grp, mcast);
}

table dmac {
  reads {
      ethernet.dstAddr : exact;
  }
  actions {
      forward;
      forward_int_eligible;
      broadcast;
      _drop;
  }
  size : 512;
}

action insert_intelem() {
  add_header(intelem);
  modify_field(intelem.timestamp, intrinsic_metadata.ingress_global_timestamp);
  modify_field(intelem.ingress_port, standard_metadata.ingress_port);
  modify_field(intelem.saved_etherType, ethernet.etherType);
  modify_field(ethernet.etherType, 0x52dc);
}

action remove_intelem() {
  modify_field(ethernet.etherType, intelem.saved_etherType);
  remove_header(intelem);
}

action _no_op() {
}

table t_insert_intelem {
  reads {
    intelem : valid;
  }
  actions {
    insert_intelem;
    _no_op;
  }
}

table t_remove_intelem {
  reads {
    intelem : valid;
  }
  actions {
    remove_intelem;
    _no_op;
  }
}

control  ingress {
  apply(dmac) {
    forward_int_eligible {
      apply(t_insert_intelem);
    }
    forward {
      apply(t_remove_intelem);
    }
  }
}
