drop table if exists connection;

create table if not exists connection (
	id serial primary key,
	xconnection_id varchar(32) not null,
	name varchar(32) not null,
	"type" varchar(16) not null,
	host varchar(128) not null,
	port integer not null,
	database varchar(128),
	"user" varchar(64) not null,
	password varchar(128) not null
);
