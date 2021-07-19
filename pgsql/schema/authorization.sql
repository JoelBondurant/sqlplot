drop table if exists "authorization" cascade;

create table if not exists "authorization" (
	"type" varchar(16) not null,
	team_xid char(32) not null,
	object_type char(16) not null,
	object_xid char(32) not null,
	primary key ("type", team_xid, object_type, object_xid),
	foreign key(team_xid) references "team"(xid)
);
